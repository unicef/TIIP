from copy import deepcopy

import factory
from faker import Faker
from project.models import Project

fake = Faker()

class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Faker('name')
    public_id = '' # default to unpublished
    featured = False
    featured_rank = 0
    image = None
    is_active = True

    draft = factory.LazyAttribute(
        lambda _: {
            "country_office": 944, # required for draft, required for publish. 
            "country": 112, # Must be the country of the country_office
            "regional_office": 14, # Must be the regional office of the country_office
            "stages": [{"id": 4}],
            "cpd": [],
            "wbs": [],
            "dhis": [], # What?
            "name": "A default name", # required for draft, required for publish. 128 chars max
            "overview": "An overview text", # required for publish. 300 words max
            "implementation_overview": "A longer narrative text.",
            "links": [], # default to empty
            "donors": [20],  # has to be this (UNICEF)
            "organisation": "56", # has to be this (UNICEF)
            "currency": 1, #default to this (USD)
            "total_budget": 0, # default to zero
            "platforms": [317], # Needs something (perhaps NA?)
            "nontech": [], # default to empty
            "hardware": [], # default to empty
            "functions": [], # default to empty
            "partners": [{"partner_name": "AOUN", "partner_type": 2}],
            "goal_area": 5,
            "start_date": "2017-01-29T22:00:00.000Z",
            "contact_name": "A User",
            "contact_email": "invent@unicef,org",
            "current_phase": 5,
            "regional_priorities": [], #can be empty
            "target_group_reached": 0, # default to zero
            "innovation_categories": [], #can be empty
            "health_focus_areas": [],
            "hsc_challenges": [],
            "capability_levels": [],
            "capability_categories": [],
            "capability_subcategories": [], 
            "unicef_leading_sector": [2], # required for publication
            "unicef_supporting_sectors": [], # can be empty
            "unicef_sector": [2], # deprecated?
        }
    )

class ProjectBuilder:
    """
    A builder class to customize a Project before building or creating it.
    You can chain methods to set various attributes, and then finalize
    creation by calling .build() or .create() with optional kwargs.
    """

    def __init__(self):
        self._stages = None
        self._published = True
        self._goal_area = None
        self._kwargs = {}

    def stages(self, stages=None):
        if stages is None:
            stages = []
        self._stages = stages
        return self

    def published(self, is_published=True):
        self._published = is_published
        return self

    def goal_area(self, area):
        self._goal_area = area
        return self

    def with_kwargs(self, **kwargs):
        """
        Store any additional kwargs to pass to the ProjectFactory later.
        This can be used if you want to set fields that aren't handled
        by the builder methods.
        """
        self._kwargs.update(kwargs)
        return self

    def build(self, **kwargs):
        """
        Build the object in memory (not saved to the DB).
        Any kwargs passed here override previously stored kwargs.
        """
        # Merge the new kwargs into _kwargs
        self._kwargs.update(kwargs)
        # Build the project using the factory, with all accumulated kwargs
        obj = ProjectFactory.build(**self._kwargs)
        self._apply_customizations(obj)
        return obj

    def create(self, **kwargs):
        """
        Create the object and save it to the DB.
        Any kwargs passed here override previously stored kwargs.
        """
        # Merge the new kwargs into _kwargs
        self._kwargs.update(kwargs)
        # Create the project using the factory, with all accumulated kwargs
        obj = ProjectFactory.create(**self._kwargs)
        self._apply_customizations(obj)
        obj.save()
        return obj

    def _apply_customizations(self, obj):
        # Apply stages if provided
        if self._stages is not None:
            obj.draft["stages"] = self._stages
            obj.data["stages"] = self._stages

        # Apply goal_area if set
        if self._goal_area is not None:
            obj.data["goal_area"] = self._goal_area

        # If published set public_id and copy draft data to data
        if self._published:
            obj.public_id = factory.Faker('uuid4')
            obj.data = deepcopy(obj.draft)
