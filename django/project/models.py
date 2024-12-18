import uuid
from copy import deepcopy
from collections import namedtuple
from functools import reduce
from typing import List, Union, Dict

from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from simple_history.models import HistoricalRecords
from sorl.thumbnail import ImageField, get_thumbnail

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models import Count, Case, When, IntegerField, F, Q, Sum, Prefetch

from core.models import (
    ExtendedModel,
    ExtendedNameOrderedSoftDeletedModel,
    ActiveQuerySet,
    SoftDeleteModel,
    ParentByIDMixin,
)
from country.models import Country, Donor, CountryOffice
from project.cache import InvalidateCacheMixin
from project.utils import remove_keys, migrate_project_phases
from user.models import UserProfile


class ProjectManager(models.Manager):
    use_in_migrations = True

    def owner_of(self, user):
        return self.filter(team=user.userprofile)

    def viewer_of(self, user):
        return self.filter(viewers=user.userprofile)

    def member_of(self, user):
        return (
            self.filter(Q(team=user.userprofile) | Q(viewers=user.userprofile))
            .distinct()
            .order_by("id")
        )

    def favorited_by(self, user):
        return self.filter(favorited_by=user.userprofile)

    # WARNING: this method is used in migration project.0016_auto_20160601_0928
    def by_organisation(self, organisation_id):  # pragma: no cover
        return self.filter(data__organisation=organisation_id)

    def published_only(self):
        return self.exclude(public_id="")

    def draft_only(self):
        return self.filter(public_id="")

    def country_managers_projects(self, user):
        user_managed_offices = list(
            user.userprofile.manager_of.values_list("id", flat=True)
        )
        if not user_managed_offices:
            qs = self.none()
        else:
            qs = self.annotate(
                co_id=Cast(
                    KeyTextTransform("country_office", "data"),
                    output_field=IntegerField(),
                )
            ).annotate(
                draft_co_id=Cast(
                    KeyTextTransform("country_office", "draft"),
                    output_field=IntegerField(),
                )
            )

            qs = qs.filter(
                Q(co_id__in=user_managed_offices)
                | Q(draft_co_id__in=user_managed_offices)
            ).order_by("-modified")
        return qs


class ProjectQuerySet(ActiveQuerySet, ProjectManager):
    def current_only(self):
        """
        Filters projects to include only those that are in a current state
        meaning they have not completed a Stage that marks initiatives as inactive.

        Warning: this is based on the project's *published* data, not the draft data
        """
        # Fetch IDs of stages that mark initiatives as inactive
        final_stage_ids = Stage.objects.filter(
            completion_marks_an_initiative_as_inactive=True
        ).values_list('id', flat=True)

        # Create a Q object that will exclude projects that have any of these stage IDs
        exclusion_q = reduce(
            lambda q, stage_id: q | Q(data__stages__contains=[{"id": stage_id}]),
            final_stage_ids,
            Q()
        )

        # Exclude projects where any of these stage IDs are in the 'stages' array
        return self.exclude(exclusion_q)


class Project(SoftDeleteModel, ExtendedModel):
    FIELDS_FOR_MEMBERS_ONLY = (
        "country_custom_answers_private",
        "start_date",
        "end_date",
    )
    FIELDS_FOR_LOGGED_IN = ("contact_email", "contact_name")

    name = models.CharField(max_length=255)
    data = JSONField(default=dict)
    draft = JSONField(default=dict)
    team = models.ManyToManyField(UserProfile, related_name="team", blank=True)
    viewers = models.ManyToManyField(
        UserProfile, related_name="viewers", blank=True)
    public_id = models.CharField(
        max_length=64,
        default="",
        help_text="<CountryCode>-<uuid>-x-<ProjectID> eg: HU9fa42491x1",
    )
    projects = ProjectManager  # deprecated, use objects instead
    objects = ProjectQuerySet.as_manager()
    # added here to avoid circular imports
    favorited_by = models.ManyToManyField(
        UserProfile, related_name="favorite_projects", blank=True
    )
    featured = models.BooleanField(default=False)
    featured_rank = models.PositiveSmallIntegerField(default=0)

    image = ImageField(upload_to="source_images", null=True, blank=True)

    def __str__(self):  # pragma: no cover
        return self.name

    @property
    def region(self):
        co_id = self.get_country_office_id()
        if co_id:
            country_office = CountryOffice.objects.get(id=co_id)
            if country_office:
                return country_office.region
        return None

    @property
    def thumbnail(self):
        try:
            if self.image:
                return get_thumbnail(self.image, f"x{settings.THUMBNAIL_HEIGHT}")
            else:  # pragma: no cover
                return None
        except OSError:  # pragma: no cover
            return None

    @property
    def image_url(self):
        return self.image.url if self.image else None

    def get_country_id(self, draft_mode=False):
        return self.draft.get("country") if draft_mode else self.data.get("country")

    def get_country(self, draft_mode=False):
        country_id = self.get_country_id(draft_mode)
        return Country.objects.get(id=int(country_id)) if country_id else None

    def get_country_office_id(self):
        if not self.public_id:
            co_id = self.draft.get("country_office")
        else:
            co_id = self.data.get("country_office")
        return co_id

    def get_project_region_id(self):
        co_id = self.get_country_office_id()
        if co_id:
            country_office = CountryOffice.objects.get(id=co_id)
            if country_office:
                return country_office.region
        return None

    def is_member(self, user):
        return (
            self.team.filter(id=user.userprofile.id).exists()
            or self.viewers.filter(id=user.userprofile.id).exists()
        )

    def is_country_user_or_admin(self, user):
        return (
            self.get_country().user_in_groups(user.userprofile)
            if self.get_country()
            else False
        )

    def get_member_data(self):
        return deepcopy(self.data)

    def get_member_draft(self):
        return deepcopy(self.draft)

    def get_non_member_data(self):
        return remove_keys(data_dict=self.data, keys=self.FIELDS_FOR_MEMBERS_ONLY)

    def get_anon_data(self):
        return remove_keys(
            data_dict=self.data,
            keys=self.FIELDS_FOR_MEMBERS_ONLY + self.FIELDS_FOR_LOGGED_IN,
        )

    @property
    def unicef_leading_sector(self):
        sector_id = self.data.get("unicef_leading_sector")
        if sector_id:
            try:
                sector = UNICEFSector.objects.get(id=sector_id[0])
                return sector_id
            except UNICEFSector.DoesNotExist:
                pass
        return []

    @property
    def unicef_supporting_sectors(self):
        sector_ids = self.data.get("unicef_supporting_sectors")
        if sector_ids:
            sectors = UNICEFSector.objects.filter(id__in=sector_ids)
            return [sector.id for sector in sectors]
        return []

    def to_representation(self, data=None, draft_mode=False):
        if data is None:
            data = self.get_member_draft() if draft_mode else self.get_member_data()

        if not data:
            return {}
        extra_data = dict(
            id=self.pk,
            name=self.draft.get("name", "") if draft_mode else self.name,
            approved=self.approval.approved if hasattr(
                self, "approval") else None,
            modified=self.modified,
            created=self.created,
            image=self.image_url,
            thumbnail=self.thumbnail.url if self.thumbnail else None,
            region=self.region,
            unicef_leading_sector=self.draft.get(
                "unicef_leading_sector", "") if draft_mode else self.unicef_leading_sector,
            unicef_supporting_sectors=self.draft.get(
                "unicef_supporting_sectors", "") if draft_mode else self.unicef_supporting_sectors
        )

        data.update(extra_data)

        return data

    def to_response_dict(self, published, draft):
        return dict(
            id=self.pk, public_id=self.public_id, published=published, draft=draft
        )

    def make_public_id(self, country_id):
        if self.public_id:
            return

        project_country = Country.objects.filter(id=country_id).first()
        if project_country:
            self.public_id = project_country.code + \
                str(uuid.uuid1()).split("-")[0]

    def approve(self):
        self.approval.approved = True
        self.approval.save()

    def disapprove(self):
        self.approval.approved = False
        self.approval.save()

    def reset_approval(self):
        if self.approval.approved is not None:
            self.approval.user = None
            self.approval.approved = None
            self.approval.reason = "Project has been republished"
            self.approval.save()

    @classmethod
    def remove_stale_donors(cls):
        from country.models import Donor

        stale_ids = []
        donor_ids = set(Donor.objects.values_list("id", flat=True))

        for p in Project.objects.all():
            if p.data and "donors" in p.data:
                published_donors = set(p.data.get("donors", []))
                stale_ids.extend(list(published_donors - donor_ids))
                p.data["donors"] = list(published_donors & donor_ids)
            if p.draft and "donors" in p.draft:
                draft_donors = set(p.draft.get("donors", []))
                stale_ids.extend(list(draft_donors - donor_ids))
                p.draft["donors"] = list(draft_donors & donor_ids)
            p.save()
        return stale_ids

    @classmethod
    def export_resource_classes(cls):  # pragma: no cover
        from project.resources import ProjectResource

        return {"projects": ("Projects", ProjectResource)}

    def unpublish(self):
        self.public_id = ""
        self.data = {}
        self.save()
        self.search.reset()


class ProjectVersion(ExtendedModel):
    version = models.IntegerField(default=1)
    project = models.ForeignKey(
        Project,
        blank=False,
        null=True,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    name = models.CharField(max_length=255)
    data = JSONField(default=dict)
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="project_versions",
        blank=True,
        null=True,
    )
    published = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "version")
        ordering = ["modified"]

    def save(self, *args, **kwargs):
        """
        Custom save method to auto-increment the version field, ignoring any gaps in the versions numbers
        """
        if not self.id:  # Only for new objects
            max_version = (
                ProjectVersion.objects.filter(project=self.project)
                .aggregate(max_version=models.Max("version"))
                .get("max_version", 0)
            ) or 0  # Default to 0 for the cases where the project has no versions, typically initiative creation
            self.version = max_version + 1
        super().save(*args, **kwargs)


@receiver(post_save, sender=Project)
def on_create_init(sender, instance, created, **kwargs):
    if created:
        ProjectApproval.objects.get_or_create(project_id=instance.id)


@receiver(post_save, sender=Project)
def migrate_project_phases_signal(sender, instance, **kwargs):
    migrate_project_phases(instance)


class PortfolioManager(models.Manager):
    use_in_migrations = True

    def is_manager(self, user: User):
        if (
            user.userprofile.global_portfolio_owner
        ):  # global portfolio owners have full rights
            return self.all()
        return self.filter(
            managers=user.userprofile
        )  # otherwise we filter for managed portfolios


class PortfolioQuerySet(ActiveQuerySet, PortfolioManager):
    pass


class Portfolio(ExtendedNameOrderedSoftDeletedModel):
    description = models.CharField(max_length=1000)
    icon = models.CharField(max_length=3, blank=True)
    managers = models.ManyToManyField(
        UserProfile, related_name="portfolios", blank=True
    )
    STATUS_DRAFT = "DR"
    STATUS_ACTIVE = "ACT"
    STATUS_ARCHIVED = "ARC"
    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Draft")),
        (STATUS_ACTIVE, _("Active")),
        (STATUS_ARCHIVED, _("Archived")),
    )

    status = models.CharField(
        max_length=3, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    investment_to_date = models.PositiveIntegerField(default=0)
    innovation_hub = models.BooleanField(default=False)
    landscape_review = models.BooleanField(default=False)
    objects = PortfolioQuerySet.as_manager()

    def get_ambition_matrix(self, project_ids: Union[List[int], None] = None):
        """
        Returns with a list of coordinates and assigned project ids for the risk impact matrix
        """
        filtered_reviews = self.review_states.filter(approved=True)
        if project_ids:
            filtered_reviews = filtered_reviews.filter(
                project_id__in=project_ids)
        if not filtered_reviews:
            return None  # pragma: no cover

        blobs = {}
        for review in filtered_reviews:
            hash = review.get_ambition_hash()

            if hash:
                if hash not in blobs:
                    blobs[hash] = {
                        "x": review.nst,
                        "y": review.nc,
                        "projects": [review.project_id],
                    }
                else:
                    blobs[hash]["projects"].append(review.project_id)
        # generate blob ratio
        blob_list = list(blobs.values())
        max_blob_size = max([len(x["projects"]) for x in blob_list])
        for blob in blob_list:
            blob["ratio"] = round(len(blob["projects"]) / max_blob_size, 2)
            blob["projects"].sort()
        return blob_list

    def get_risk_impact_matrix(self, project_ids: Union[List[int], None] = None):
        """
        Returns with a list of coordinates and assigned project ids for the risk-impact matrix
        """
        filtered_reviews = self.review_states.filter(approved=True)
        if project_ids:
            filtered_reviews = filtered_reviews.filter(
                project_id__in=project_ids)
        if not filtered_reviews:
            return None  # pragma: no cover

        blobs = {}
        for review in filtered_reviews:
            hash = review.get_impact_hash()
            if hash:
                if hash not in blobs:
                    blobs[hash] = {
                        "x": review.impact,
                        "y": review.ra,
                        "projects": [review.project_id],
                    }
                else:
                    blobs[hash]["projects"].append(review.project_id)
        # generate blob ratio
        blob_list = list(blobs.values())
        max_blob_size = max([len(x["projects"]) for x in blob_list])
        for blob in blob_list:
            blob["ratio"] = round(len(blob["projects"]) / max_blob_size, 2)
            blob["projects"].sort()
        return blob_list

    def get_problem_statement_matrix(self):
        tresholds = settings.PORTFOLIO_PROBLEMSTATEMENT_TRESHOLDS

        neglected_filter = Q(num_projects__lt=tresholds["MODERATE"])
        moderate_filter = Q(
            num_projects__gte=tresholds["MODERATE"], num_projects__lt=tresholds["HIGH"]
        )
        high_filter = Q(num_projects__gte=tresholds["HIGH"])

        when_statement = dict(
            projectportfoliostate__approved=True, then=F("projectportfoliostate__id")
        )

        base_qs = self.problem_statements.annotate(
            num_projects=Count(
                Case(When(**when_statement), output_field=IntegerField()), distinct=True
            )
        )

        neglected_qs = base_qs.filter(neglected_filter)
        moderate_qs = base_qs.filter(moderate_filter)
        high_qs = base_qs.filter(high_filter)

        return {
            "neglected": list(neglected_qs.values_list("pk", flat=True)),
            "moderate": list(moderate_qs.values_list("pk", flat=True)),
            "high_activity": list(high_qs.values_list("pk", flat=True)),
        }


class ProblemStatement(ExtendedNameOrderedSoftDeletedModel):
    description = models.CharField(max_length=1024)
    portfolio = models.ForeignKey(
        Portfolio,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="problem_statements",
    )

    # This is a workaround for some strange issue regarding ActiveQuerySet
    class Meta:
        default_manager_name = "objects"
        ordering = ["name"]


class ProjectApproval(ExtendedModel):
    project = models.OneToOneField(
        "Project", related_name="approval", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        UserProfile,
        blank=True,
        null=True,
        help_text="Administrator who approved the project",
        on_delete=models.CASCADE,
    )
    approved = models.BooleanField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    history = HistoricalRecords(excluded_fields=["project", "created"])

    def __str__(self):
        return "Approval for {}".format(self.project.name)


class File(ExtendedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    data = models.BinaryField()


class DigitalStrategy(
    ParentByIDMixin, InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel
):
    GROUP_CHOICES = (
        ("Client", _("Client")),
        ("Provider", _("Provider")),
        ("System", _("System")),
        ("Data service", _("Data service")),
    )
    group = models.CharField(max_length=255, choices=GROUP_CHOICES)
    parent = models.ForeignKey(
        "DigitalStrategy",
        related_name="strategies",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        parent = " [{}]".format(self.parent.name) if self.parent else ""
        return "[{}]{} {}".format(self.group, parent, self.name)

    class Meta:
        verbose_name = "WHO Digital Health Intervention (DHI)"
        verbose_name_plural = (
            "WHO Digital Health Interventions (=UNICEF Health Capability Categories)"
        )
        ordering = ["group", "name"]


class HSCGroup(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta:
        verbose_name = "WHO Health System Challenge Group"
        ordering = ["name"]


class HSCChallengeQuerySet(ActiveQuerySet):
    FakeChallenge = namedtuple("FakeChallenge", ["name", "challenge"])


class HSCChallenge(
    ParentByIDMixin, InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel
):
    group = models.ForeignKey(
        HSCGroup, on_delete=models.CASCADE, related_name="challenges"
    )

    def __str__(self):
        return "({}) {}".format(self.group.name, self.name)

    class Meta:
        verbose_name = "WHO Health System Challenge"
        verbose_name_plural = "WHO Health System Challenges"
        ordering = ["group", "name"]

    objects = HSCChallengeQuerySet.as_manager()


class HealthCategory(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name = "WHO Health Category"
        verbose_name_plural = "WHO Health Categories"


class HealthFocusArea(
    ParentByIDMixin, InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel
):
    health_category = models.ForeignKey(
        HealthCategory, related_name="health_focus_areas", on_delete=models.CASCADE
    )

    def __str__(self):
        return "[{}] {}".format(self.health_category.name, self.name)

    class Meta:
        verbose_name = "WHO Health Focus Area"
        verbose_name_plural = "WHO Health Focus Areas"
        ordering = ["health_category__name", "name"]


class ApprovalState(models.Model):
    APPROVED = 1
    PENDING = 2
    DECLINED = 3

    STATES = (
        (APPROVED, _("Approved")),
        (PENDING, _("Pending")),
        (DECLINED, _("Declined")),
    )

    state = models.IntegerField(choices=STATES, default=APPROVED)
    added_by = models.ForeignKey(
        UserProfile, blank=True, null=True, on_delete=models.SET_NULL
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__important_fields = ["state"]
        for field in self.__important_fields:
            setattr(self, "__original_%s" % field, getattr(self, field))


class TechnologyPlatform(
    InvalidateCacheMixin, ApprovalState, ExtendedNameOrderedSoftDeletedModel
):
    
    comment = models.CharField(max_length=1024, blank=True)
    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        related_name="software_tags",
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "Software"
        verbose_name_plural = "Software"


class HardwarePlatform(
    InvalidateCacheMixin, ApprovalState, ExtendedNameOrderedSoftDeletedModel
):
    
    comment = models.CharField(max_length=1024, blank=True)
    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        related_name="hardaware_tags",
        on_delete=models.SET_NULL
    )
    
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Hardware Platform(s) and Physical Product(s)"


class NontechPlatform(
    InvalidateCacheMixin, ApprovalState, ExtendedNameOrderedSoftDeletedModel
):
    
    comment = models.CharField(max_length=1024, blank=True)
    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        related_name="nontechnology_tags",
        on_delete=models.SET_NULL
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Programme Innovation(s) and Non-Technology Platform(s)"


class PlatformFunction(
    InvalidateCacheMixin, ApprovalState, ExtendedNameOrderedSoftDeletedModel
):
    
    comment = models.CharField(max_length=1024, blank=True)
    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        related_name="platform_tags",
        on_delete=models.SET_NULL
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Function(s) of Platform"


@receiver(post_save, sender=PlatformFunction)
@receiver(post_save, sender=NontechPlatform)
@receiver(post_save, sender=HardwarePlatform)
@receiver(post_save, sender=TechnologyPlatform)
def process_approval_states(sender, instance, created, **kwargs):
    if not created and instance.__original_state != instance.state:
        from project.tasks import notify_user_about_approval

        if sender == TechnologyPlatform:
            data_key = "platforms"
            field_name = "Software"
        elif sender == HardwarePlatform:  # pragma: no cover
            data_key = "hardware"
            field_name = "Hardware"
        elif sender == NontechPlatform:  # pragma: no cover
            data_key = "nontech"
            field_name = "Programme innovation/Non-technology"
        elif sender == PlatformFunction:  # pragma: no cover
            data_key = "functions"
            field_name = "Function"
        else:  # pragma: no cover
            return

        if instance.state == ApprovalState.DECLINED:
            projects = Project.objects.filter(
                Q(**{f"data__{data_key}__contains": [instance.id]})
                | Q(**{f"draft__{data_key}__contains": [instance.id]})
            )

            for project in projects:
                if project.public_id and data_key in project.data:
                    project.data[data_key] = [
                        item for item in project.data[data_key] if item != instance.id
                    ]
                if data_key in project.draft:
                    project.draft[data_key] = [
                        item for item in project.draft[data_key] if item != instance.id
                    ]
                project.save(update_fields=["data", "draft"])

            notify_user_about_approval.apply_async(
                args=(
                    "decline",
                    instance._meta.model_name,
                    instance.pk,
                    field_name
                )
            )
        elif instance.state == ApprovalState.APPROVED:
            notify_user_about_approval.apply_async(
                args=(
                    "approve",
                    instance._meta.model_name,
                    instance.pk,
                    field_name
                )
            )


class UNICEFResultArea(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    goal_area = models.ForeignKey(
        "UNICEFGoal", related_name="result_areas", on_delete=models.CASCADE
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Result Areas"

    def __str__(self):  # pragma: no cover
        return "[{}] {}".format(self.goal_area.name, self.name)


class UNICEFCapabilityLevel(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    goal_area = models.ForeignKey(
        "UNICEFGoal", related_name="capability_levels", on_delete=models.CASCADE
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Capability Levels"

    def __str__(self):  # pragma: no cover
        return "[{} - {}] {}".format(
            self.goal_area.name, self.goal_area.capability_level_question, self.name
        )


class UNICEFCapabilityCategory(
    InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel
):
    goal_area = models.ForeignKey(
        "UNICEFGoal", related_name="capability_categories", on_delete=models.CASCADE
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Capability Categories"

    def __str__(self):  # pragma: no cover
        return "[{} - {}] {}".format(
            self.goal_area.name, self.goal_area.capability_category_question, self.name
        )


class UNICEFCapabilitySubCategory(
    InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel
):
    goal_area = models.ForeignKey(
        "UNICEFGoal", related_name="capability_subcategories", on_delete=models.CASCADE
    )

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Capability Sub Categories"

    def __str__(self):  # pragma: no cover
        return "[{} - {}] {}".format(
            self.goal_area.name,
            self.goal_area.capability_subcategory_question,
            self.name,
        )


class UNICEFGoal(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    capability_level_question = models.CharField(max_length=512)
    capability_category_question = models.CharField(max_length=512)
    capability_subcategory_question = models.CharField(max_length=512)

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Goal Areas"

    def __str__(self):  # pragma: no cover
        return "{}".format(self.name)


class UNICEFSector(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "UNICEF Sectors"


class RegionalPriority(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    region = models.IntegerField(
        choices=CountryOffice.REGIONS, null=True, blank=True)

    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Regional Priorities"


class InnovationCategory(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Innovation Categories"


class InnovationWay(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Innovation Ways"


class CPD(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "CPD and annual work plan"


class ISC(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "Information Security Classification"


class ProjectImport(ExtendedModel):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    csv = models.FileField()
    headers = ArrayField(models.CharField(
        max_length=512), blank=True, null=True)
    mapping = JSONField(default=dict)
    imported = models.TextField(null=True, blank=True, default="")
    failed = models.TextField(null=True, blank=True, default="")
    status = models.BooleanField(null=True, blank=True)

    def __str__(self):  # pragma: no cover
        return self.csv.name


class ProjectImportV2(ExtendedModel):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    status = models.BooleanField(
        null=True, blank=True)  # TODO: maybe remove this
    header_mapping = JSONField(default=dict, blank=True)
    country = models.ForeignKey(
        Country, null=True, blank=True, on_delete=models.SET_NULL
    )
    country_office = models.ForeignKey(
        CountryOffice, null=True, blank=True, on_delete=models.SET_NULL
    )
    donor = models.ForeignKey(
        Donor, null=True, blank=True, on_delete=models.SET_NULL)
    filename = models.CharField(max_length=256, null=True, blank=True)
    sheet_name = models.CharField(max_length=256, null=True, blank=True)
    draft = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "filename", "sheet_name")

    def __str__(self):  # pragma: no cover
        return self.filename if self.filename else self.pk


class ImportRow(models.Model):
    data = JSONField(default=dict)
    original_data = JSONField(default=dict)
    project = models.ForeignKey(Project, null=True, on_delete=models.SET_NULL)
    parent = models.ForeignKey(
        ProjectImportV2, null=True, related_name="rows", on_delete=models.SET_NULL
    )


class BaseScoreManager(ActiveQuerySet, models.Manager):
    use_in_migrations = True
    use_for_related_fields = True


class BaseScore(SoftDeleteModel, ExtendedModel):
    BASE_CHOICES = [(i, i) for i in range(1, 6)]
    psa = models.ManyToManyField(
        ProblemStatement, blank=True
    )  # Problem Statement Alignment
    rnci = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Reach: Number of Children Impacted
    ratp = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Reach: Addressing Target Populations
    ra = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Risk Assessment
    ee = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Evidence of Effectiveness
    nst = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Newness of Solution (Tool)
    nc = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Newness of Challenge
    ps = models.IntegerField(
        choices=BASE_CHOICES, null=True, blank=True
    )  # Path to Scale
    overall_reviewer_feedback = models.CharField(
        max_length=1024, null=True, blank=True)

    objects = BaseScoreManager.as_manager()

    class Meta:
        abstract = True
        default_manager_name = "objects"


class ProjectPortfolioStateManager(ActiveQuerySet, models.Manager):
    use_in_migrations = True
    use_for_related_fields = True


class ProjectPortfolioState(BaseScore):
    SCALE_CHOICES = (
        (1, _("1 - Ideation")),
        (2, _("2 - Research & Development")),
        (3, _("3 - Proof of Concept")),
        (4, _("4 - Transition to Scale")),
        (5, _("5 - Scaling")),
        (6, _("6 - Sustainable Scale")),
    )

    impact = models.IntegerField(
        choices=BaseScore.BASE_CHOICES, null=True, blank=True)
    scale_phase = models.IntegerField(
        choices=SCALE_CHOICES, null=True, blank=True)
    portfolio = models.ForeignKey(
        Portfolio, related_name="review_states", on_delete=models.CASCADE
    )
    project = models.ForeignKey(
        Project, related_name="review_states", on_delete=models.CASCADE
    )
    reviewed = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)

    objects = ProjectPortfolioStateManager.as_manager()

    class Meta:
        unique_together = ("portfolio", "project")
        default_manager_name = "objects"
        base_manager_name = "objects"

    def __str__(self):  # pragma: no cover
        return f"{self.portfolio}: {self.project}"

    def assign_questionnaire(self, user: UserProfile):
        return ReviewScore.objects.get_or_create(reviewer=user, portfolio_review=self)

    def get_impact_hash(self):
        return f"{self.impact}-{self.ra}" if self.reviewed else None

    def get_ambition_hash(self):
        return f"{self.nst}-{self.nc}" if self.reviewed else None


class ReviewScore(BaseScore):
    reviewer = models.ForeignKey(
        UserProfile, related_name="review_scores", on_delete=models.CASCADE
    )
    portfolio_review = models.ForeignKey(
        ProjectPortfolioState, related_name="review_scores", on_delete=models.CASCADE
    )
    psa_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # PSA - reviewer's comment field
    rnci_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # RNCI - reviewer's comment field
    ratp_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # RATP - reviewer's comment field
    ra_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # Risk Assessment - reviewer's comment field
    ee_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # EE - reviewer's comment field
    nst_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # NST - reviewer's comment field
    nc_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # NC - reviewer's comment field
    ps_comment = models.CharField(
        max_length=255, null=True, blank=True
    )  # PS - reviewer's comment field

    STATUS_PENDING = "PD"
    STATUS_DRAFT = "DR"
    STATUS_COMPLETE = "CMP"
    STATUS_CHOICES = (
        (STATUS_PENDING, _("Pending")),
        (STATUS_DRAFT, _("Draft")),
        (STATUS_COMPLETE, _("Complete")),
    )

    status = models.CharField(
        max_length=3, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    def __str__(self):  # pragma: no cover
        return f"{self.reviewer} - {self.portfolio_review.project} - {self.portfolio_review.portfolio}"

    class Meta:
        unique_together = ("reviewer", "portfolio_review")
        default_manager_name = "objects"

    def get_project_data(self):  # pragma: no cover
        return self.portfolio_review.project.to_representation()

    def get_portfolio(self):  # pragma: no cover
        return self.portfolio_review.portfolio


class Stage(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    name = models.CharField(max_length=128)
    order = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
    tooltip = models.CharField(max_length=256, blank=True, null=True)
    link = models.URLField(max_length=100, blank=True, null=True)
    completion_marks_an_initiative_as_inactive = models.BooleanField(
        help_text="When this phase is marked as completed (with an end date) it means that the initiative is no longer active.<br>It will not move automatically to a following phase, but will stay in this phase.", default=False)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Phase of initiative"
        verbose_name_plural = "Phases of initiative"

    def __str__(self):  # pragma: no cover
        return self.name

    @classmethod
    def calc_current_phase(cls, stages: List[Dict]):
        all_stages = list(cls.objects.order_by(
            "order").values_list("id", flat=True))
        if not stages:  # when no phases are selected the current phase is the first one
            return all_stages[0]

        stage_ids = [stage["id"] for stage in stages]
        # get the completed phases of the initiative and order them
        selected_stages = cls.objects.filter(
            id__in=stage_ids).order_by("order")
        # get the last phase from initiative's completed phases
        last_stage = selected_stages.last()

        # apply the business requirements
        if not last_stage.completion_marks_an_initiative_as_inactive:  # selected phase's checkbox unchecked
            # compute if there are already previous completed end phases (checkbox=checked)
            completed_stages = selected_stages.filter(
                completion_marks_an_initiative_as_inactive=True)
            if completed_stages:  # if there completed end phases
                current = last_stage.id
            else:  # if there are not completed end phases
                if last_stage.id != all_stages[-1]:  # not the last in list
                    current = all_stages[all_stages.index(
                        last_stage.id) + 1]  # get the next phase
                else:  # the last in list
                    current = last_stage.id  # set this phase as current
        else:  # selected phase's checkbox checked
            current = last_stage.id  # set this phase as current

        return current


class Phase(InvalidateCacheMixin, ExtendedNameOrderedSoftDeletedModel):
    class Meta(ExtendedNameOrderedSoftDeletedModel.Meta):
        verbose_name_plural = "[DEPRECATED] Phase of Initiative"


class Solution(ExtendedNameOrderedSoftDeletedModel):
    # Constants to define the phases of a Solution
    PHASES = [
        (0, _("Pilot")),
        (1, _("Acceleration")),
        (2, _("Scale")),
    ]

    # Fields
    portfolios = models.ManyToManyField(Portfolio, related_name="solutions",blank=True)
    countries = models.ManyToManyField(Country, through="CountrySolution")
    problem_statements = models.ManyToManyField(ProblemStatement,blank=True)
    phase = models.IntegerField(choices=PHASES)
    open_source_frontier_tech = models.BooleanField()
    learning_investment = models.BooleanField()
    people_reached_override = models.PositiveIntegerField(
        help_text="Override country based calculation", null=True, blank=True
    )
    is_active = models.BooleanField()
    set_aside_2021 = models.BooleanField(default=False)
    set_aside_2022 = models.BooleanField(default=False)

    # Properties
    @property
    def people_reached(self):
        """
        The number of people reached by the solution.
        """
        if self.people_reached_override:
            return self.people_reached_override
        else:
            return (
                self.countrysolution_set.aggregate(Sum("people_reached"))[
                    "people_reached__sum"
                ]
                or 0
            )

    @people_reached.setter
    def people_reached(self, value):
        """
        Sets the number of people reached by the solution.
        """
        self.people_reached_override = value

    @property
    def regions(self) -> List:
        """
        The regions of the countries where the solution has been implemented.
        """
        return list(set(self.countrysolution_set.values_list("region", flat=True)))

    @property
    def regions_display(self):
        """
        The display names of the regions of the countries where the solution has been implemented.
        """
        return [CountryOffice.REGIONS[r][1] for r in self.regions]

    # Class methods
    @classmethod
    def prefetch_related_objects(cls):
        """
        Returns a Prefetch object that fetches all related objects needed for Solution.to_representation.
        """
        return (
            Prefetch("problem_statements"),
            Prefetch("portfolios"),
            Prefetch(
                "countrysolution_set",
                queryset=CountrySolution.objects.select_related("country"),
            ),
        )

    # Methods
    def get_portfolio_problem_statements(self):
        """
        Get a list of dictionaries that represent the portfolios and their associated problem statements for the current
        solution.

        Returns:
            A list of dictionaries, where each dictionary contains the following keys:
                - portfolio_id (int): The ID of the portfolio.
                - problem_statements (list of int): The IDs of the problem statements associated with the portfolio.

        Example:
            >>> solution = Solution.objects.get(pk=1)
            >>> portfolios = solution.get_portfolio_problem_statements()
            >>> print(portfolios)
            [
                {'portfolio_id': 1, 'problem_statements': [3, 51]},
                {'portfolio_id': 5, 'problem_statements': [1, 51]}
            ]
        """
        # Create an empty dictionary to group problem statements by portfolio ID
        portfolio_dict = {}
        problem_statements = self.problem_statements.values()
        # Loop through all problem statements and group them by portfolio ID
        for ps in problem_statements:
            portfolio_id = ps["portfolio_id"]
            if portfolio_id not in portfolio_dict:
                portfolio_dict[portfolio_id] = {
                    "portfolio_id": portfolio_id,
                    "problem_statements": [],
                }
            portfolio_dict[portfolio_id]["problem_statements"].append(ps["id"])

        # Convert the dictionary to a list of objects
        portfolio_list = list(portfolio_dict.values())
        return portfolio_list

    def to_representation(self):
        """
        Returns a dictionary representing this Solution instance, to be used as a response payload in an API.
        The method first uses the `prefetch_related` method to efficiently fetch related objects using the
        related managers defined on the model. Then it constructs a dictionary containing the Solution model payload:

        Parameters:
        ----------
            None.

        Returns:
        -------
            data: dict:

        Example:
        -------
        {
            'id': 1,
            'created': datetime.datetime(2022, 1, 1, 0, 0),
            'modified': datetime.datetime(2022, 2, 1, 0, 0),
            'name': 'Solution 1',
            'is_active': True,
            'phase': 2,
            'open_source_frontier_tech': True,
            'learning_investment': False,
            'portfolios': [1, 2],
            'problem_statements': [3, 4],
            'people_reached': 100000,
            'country_solutions': [
                {'id': 1, 'country': 2, 'people_reached': 10000, 'region': '1'},
                {'id': 2, 'country': 3, 'people_reached': 20000, 'region': '2'}
            ],
            'portfolio_problem_statements': [
                {'portfolio_id': 1, 'problem_statements': [3, 4]},
                {'portfolio_id': 2, 'problem_statements': [4, 5]}
            ],
            'set_aside_2021': True,
            'set_aside_2022': False,
        }
        """
        # Use the Prefetch object to fetch related objects efficiently
        self = Solution.objects.prefetch_related(*self.prefetch_related_objects()).get(
            pk=self.pk
        )

        portfolios = self.portfolios.values_list("id", flat=True)
        problem_statements = self.problem_statements.values_list(
            "id", flat=True)
        country_solutions = self.countrysolution_set.values(
            "id", "country", "people_reached", "region"
        )

        data = {
            "id": self.pk,
            "created": self.created,
            "modified": self.modified,
            "name": self.name,
            "is_active": self.is_active,
            "phase": self.phase,
            "open_source_frontier_tech": self.open_source_frontier_tech,
            "learning_investment": self.learning_investment,
            "portfolios": list(portfolios),
            "problem_statements": list(problem_statements),
            "people_reached": self.people_reached,
            "country_solutions": list(country_solutions),
            "portfolio_problem_statements": self.get_portfolio_problem_statements(),
            "set_aside_2021": self.set_aside_2021,
            "set_aside_2022": self.set_aside_2022,
        }

        return data


class CountrySolution(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE)
    people_reached = models.PositiveIntegerField()
    region = models.IntegerField(choices=CountryOffice.REGIONS)

    class Meta:
        order_with_respect_to = "country"
        unique_together = [
            ("country", "solution"),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.solution} in {self.country}"