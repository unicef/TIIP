import json
import logging
import traceback
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin

import requests
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template import loader
from django.utils import timezone
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from core.utils import send_mail_wrapper
from country.models import Country, Donor, DonorCustomQuestion
from scheduler.celery import app
from user.models import Organisation
from .models import Project, InteroperabilityLink
from .serializers import ProjectDraftSerializer

logger = get_task_logger(__name__)


def exclude_specific_project_stages(projects, filter_key_prefix='draft'):
    try:
        unicef = Donor.objects.get(name='UNICEF')
    except Donor.DoesNotExist:  # pragma: no cover
        pass
    else:
        try:
            question = DonorCustomQuestion.objects.get(donor=unicef, question='Stage')
        except DonorCustomQuestion.DoesNotExist:  # pragma: no cover
            pass
        else:
            stages_to_exclude = ['Discontinued', "Scale and Handover"]
            filtered_projects = Project.objects.none()
            key = f"{filter_key_prefix}__donor_custom_answers__{unicef.id}__{question.id}"
            for stage in stages_to_exclude:
                condition = {f"{key}__icontains": stage}
                filtered_projects = filtered_projects | projects.filter(**condition)

            if filtered_projects:
                projects = projects.exclude(id__in=filtered_projects)
    return projects


@app.task(name="project_review_requested_notification")
def project_review_requested_notification():
    """
    Sends notification if a project needs review by an user
    """
    from project.models import ReviewScore
    from user.models import UserProfile

    incomplete_reviews = ReviewScore.objects.filter(complete=False).filter(
        modified__lt=timezone.now() - timezone.timedelta(days=settings.NOTIFICATION_PROJECT_REVIEW_DAYS))

    if not incomplete_reviews:  # pragma: no cover
        return

    # limit number of mails sent
    if not settings.EMAIL_SENDING_PRODUCTION:
        reviews = ReviewScore.objects.filter(id=incomplete_reviews.first().id)

    for review in reviews:
        try:
            profile = UserProfile.objects.get(id=review.reviewer)
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass
        else:
            subject = _("One of your requested project reviews has not been completed yet")
            details = _('The following project review has been incomplete for 30 days, '
                        'Please consider reviewing it: ')
            send_mail_wrapper(
                subject=subject,
                email_type='reminder_project_review_template',
                to=profile.user.email,
                language=profile.language or settings.LANGUAGE_CODE,
                context={
                    'reviewscore': review,
                    'name': profile.name,
                    'details': details,
                }
            )


@app.task(name="project_still_in_draft_notification")
def project_still_in_draft_notification():
    """
    Sends notification if a project is in draft state for over a month.
    """
    from user.models import UserProfile

    projects = Project.objects.draft_only().filter(modified__lt=timezone.now() - timezone.timedelta(days=31))

    projects = exclude_specific_project_stages(projects)

    if not projects:  # pragma: no cover
        return

    # limit emails
    if not settings.EMAIL_SENDING_PRODUCTION:
        projects = Project.objects.filter(id=projects.first().id)

    project_team_members = set(projects.values_list('team', flat=True))

    for member in project_team_members:
        try:
            profile = UserProfile.objects.get(id=member)
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass
        else:
            member_projects = [project for project in projects.filter(team=member)]
            subject = _("One or more of your projects have not been published yet")
            details = _('The following project(s) have been draft only for over a month, '
                        'please consider publishing so they become visible in the search or on the map: ')
            send_mail_wrapper(
                subject=subject,
                email_type='reminder_common_template',
                to=profile.user.email,
                language=profile.language or settings.LANGUAGE_CODE,
                context={
                    'projects': member_projects,
                    'name': profile.name,
                    'details': details,
                }
            )


@app.task(name="published_projects_updated_long_ago")
def published_projects_updated_long_ago():
    """
    Sends notification if a project is published but not updated in the last 6 months
    """
    from user.models import UserProfile

    projects = Project.objects.published_only().filter(modified__lt=timezone.now() - timezone.timedelta(days=180))

    projects = exclude_specific_project_stages(projects, filter_key_prefix='data')

    if not projects:  # pragma: no cover
        return

    # limit emails
    if not settings.EMAIL_SENDING_PRODUCTION:
        projects = Project.objects.filter(id=projects.first().id)

    project_team_members = set(projects.values_list('team', flat=True))

    for member in project_team_members:
        try:
            profile = UserProfile.objects.get(id=member)
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass
        else:
            member_projects = [project for project in projects.filter(team=member)]
            subject = _("One or more of your projects have not been updated for 6 months")
            details = _('Please check in to keep the project data current by verifying the following project(s):')
            send_mail_wrapper(
                subject=subject,
                email_type='reminder_common_template',
                to=profile.user.email,
                language=profile.language or settings.LANGUAGE_CODE,
                context={
                    'projects': member_projects,
                    'name': profile.name,
                    'details': details,
                }
            )


@app.task(name="send_project_approval_digest")
def send_project_approval_digest():
    countries = Country.objects.exclude(users=None)
    for country in countries:
        if country.project_approval:
            projects = Project.objects.filter(data__country=country.id, approval__approved__isnull=True)

            if not projects:
                return

            email_mapping = defaultdict(list)
            for profile in country.users.all():
                email_mapping[profile.language].append(profile.user.email)

            for language, email_list in email_mapping.items():
                context = {'country_name': country.name, 'projects': projects}

                send_mail_wrapper(subject='Action required: New projects awaiting approval',
                                  email_type='status_report',
                                  to=email_list,
                                  language=language,
                                  context=context)


@app.task(name="sync_project_from_odk")
def sync_project_from_odk():  # pragma: no cover
    base_url = '{}://{}'.format(settings.ODK_SERVER_PROTOCOL, settings.ODK_SERVER_HOST)
    form_url = '/web-ui/tables/{}/export/JSON/showDeleted/false'.format(settings.ODK_TABLE_NAME)
    login_url = urljoin(base_url, '/web-ui/login')
    import_url = urljoin(base_url, form_url)

    email_html_template = loader.get_template('email/odk_import_email.html')
    email_subject = ugettext('Project imported from ODK')

    s = requests.Session()
    login_response = s.post(login_url, data=settings.ODK_CREDENTIALS)
    login_response.raise_for_status()
    res = s.get(import_url)
    res.raise_for_status()

    interoperability_links = InteroperabilityLink.objects.all()

    def send_imported_email(project, user):
        html_message = email_html_template.render({'project': project,
                                                   'user_email': user.email,
                                                   'language': user.userprofile.language})
        send_mail(
            subject=email_subject,
            message='',
            from_email=settings.FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message)

    def uuid_parser(value):
        return value.replace('uuid:', '')

    def escaped_int_converter(value):
        if isinstance(value, str) and value.startswith("'"):
            value = value.replace("'", '')
        return int(value)

    def list_parser(list):
        return json.loads(list)

    def string_to_list(text):
        return list(filter(lambda s: s, text.split(',')))

    def first_level_converter(value, column_type, project, int_link_collection):
        default_nld = {
            'clients': 0,
            'facilities': 0,
            'health_workers': 0
        }
        if column_type == 'name':
            project['name'] = value
        elif column_type == 'organization':
            try:
                project['organisation'] = escaped_int_converter(value)
            except ValueError:
                (org, success) = Organisation.objects.get_or_create(name=value)
                project['organisation'] = org.id
        elif column_type == 'country':
            project['country'] = escaped_int_converter(value)
        elif 'platforms' in column_type:
            platforms = project.get('platforms', [])
            value = escaped_int_converter(value)
            project['platforms'] = platforms + [{'id': value}]
        elif column_type == 'clients':
            nld = project.get('national_level_deployment', dict(default_nld))
            nld['clients'] = escaped_int_converter(value)
            project['national_level_deployment'] = nld
        elif column_type == 'facilities':
            nld = project.get('national_level_deployment', dict(default_nld))
            nld['facilities'] = escaped_int_converter(value)
            project['national_level_deployment'] = nld
        elif column_type == 'health_workers':
            nld = project.get('national_level_deployment', dict(default_nld))
            nld['health_workers'] = escaped_int_converter(value)
            project['national_level_deployment'] = nld
        elif column_type == 'contact_email':
            project['contact_email'] = value
        elif column_type == 'contact_name':
            project['contact_name'] = value
        elif column_type == 'donors':
            project['donors'] = string_to_list(value)
        elif column_type == 'end_date':
            project['end_date'] = value
        elif column_type == 'geographic_scope':
            project['geographic_scope'] = value
        elif column_type == 'government_investor':
            project['government_investor'] = escaped_int_converter(value)
        elif column_type == 'health_focus_areas':
            as_list = list_parser(value)
            project['health_focus_areas'] = list(map(lambda s: escaped_int_converter(s), as_list))
        elif column_type == 'health_information_systems':
            as_list = list_parser(value)
            project['his_bucket'] = list(map(lambda s: escaped_int_converter(s), as_list))
        elif column_type == 'health_system_challenges':
            as_list = list_parser(value)
            project['hsc_challenges'] = list(map(lambda s: escaped_int_converter(s), as_list))
        elif column_type == 'implementation_dates':
            project['implementation_dates'] = value
        elif column_type == 'implementation_overview':
            project['implementation_overview'] = value
        elif column_type == 'implementing_partners':
            project['implementing_partners'] = string_to_list(value)
        elif column_type == 'licenses':
            as_list = list_parser(value)
            project['licenses'] = list(map(lambda s: escaped_int_converter(s), as_list))
        elif column_type == 'mobile_application':
            project['mobile_application'] = value
        elif column_type == 'repository':
            project['repository'] = value
        elif column_type == 'start_date':
            project['start_date'] = value
        elif column_type == 'wiki':
            project['wiki'] = value
        elif column_type == 'interoperability_standards':
            as_list = list_parser(value)
            project['interoperability_standards'] = list(map(lambda s: escaped_int_converter(s), as_list))
        elif 'interoperability_link_' in column_type and '_url' not in column_type:
            id = None
            try:
                id = escaped_int_converter(value)
            except ValueError:
                logging.error('Value error, received: {}'.format(value))
                pass
            if id:
                il_obj = next((item for item in int_link_collection if item["id"] == id), None)
                il_obj['selected'] = True
                il_obj['odk_name'] = '{}_url'.format(column_type)

    def second_level_converter(value, column_type, project, context):
        if 'dhi' in column_type:
            platform = project['platforms'][context["dhi_index"]]
            if platform:
                as_list = list_parser(value)
                platform['strategies'] = list(map(lambda s: escaped_int_converter(s), as_list))
            context["dhi_index"] += 1
        elif 'interoperability_link_' in column_type and '_url' in column_type:
            il_obj = next((item for item in context['int_link_collection'] if item["odk_name"] == column_type), None)
            if il_obj:
                il_obj['link'] = value.lower()

    def odk_columns_parser(columns, interoperability_links):
        int_link_collection = list(map(lambda il: {'id': il.id, 'odk_name': None}, interoperability_links))
        project = dict()
        context = dict(int_link_collection=int_link_collection, dhi_index=0)
        for column in columns:
            column_type = column.get('column', None)
            value = column.get('value', None)
            if column_type and value:
                try:
                    first_level_converter(value, column_type, project, int_link_collection)
                except Exception:
                    traceback.print_exc()

        for column in columns:
            column_type = column.get('column', None)
            value = column.get('value', None)
            if column_type and value:
                try:
                    second_level_converter(value, column_type, project, context)
                except IndexError:
                    logging.error('{} has invalid / missing value: {}'.format(column_type, value))
                except Exception:
                    traceback.print_exc()

        for int_link_dict in int_link_collection:
            int_link_dict.pop('odk_name', None)
        project['interoperability_links'] = int_link_collection
        return project

    def parse_odk_data(row, odk_etag, odk_id, odk_extra_data, interoperability_links):
        p = odk_columns_parser(row.get('orderedColumns'), interoperability_links)
        p['odk_etag'] = odk_etag
        p['odk_id'] = odk_id
        p['odk_extra_data'] = odk_extra_data
        return p

    def new_or_updated_serializer(data, existing=None):
        if existing:
            return ProjectDraftSerializer(existing, data=data, context={'preserve_etag': True})
        else:
            return ProjectDraftSerializer(data=data)

    def serialize_and_save(row, odk_etag, odk_id, odk_extra_data, existing, user_email, interoperability_links):
        parsed = parse_odk_data(row, odk_etag, odk_id, odk_extra_data, interoperability_links)
        serialized = new_or_updated_serializer(parsed, existing)
        try:
            if not serialized.is_valid():
                logging.error(serialized.errors)
                for error in serialized.errors:
                    parsed.pop(error, None)
                serialized = new_or_updated_serializer(parsed, existing)
                serialized.is_valid(raise_exception=True)

            if existing:
                serialized.save()
            else:
                u = User.objects.get(email=user_email)
                project = serialized.save(owner=u.userprofile)
                send_imported_email(project, u)
        except ObjectDoesNotExist:
            logging.error('No user with following email: {}'.format(user_email))
        except ValidationError:
            logging.warning('Validation error/s:')
            logging.warning(serialized.errors)

    def save_or_update_project(row, user_email, odk_etag, odk_id, odk_extra_data, interoperability_links):
        existing = None
        try:
            existing = Project.objects.get(odk_id=odk_id)
        except ObjectDoesNotExist:
            pass
        if not existing:
            logging.error('Does not exist in DHA database: importing')
            serialize_and_save(row, odk_etag, odk_id, odk_extra_data, None, user_email, interoperability_links)
        elif existing.odk_etag is None:
            logging.error('Overridden by ui: nothing to do')
        elif existing.odk_etag != odk_etag:
            logging.error('Exist in DHA database, but new version found in ODK: updating')
            serialize_and_save(row, odk_etag, odk_id, odk_extra_data, existing, None, interoperability_links)
        else:
            logging.error('Already present and same version: nothing to do')

    def start_sync(rows, interoperability_links):
        logging.error('ODK IMPORT TASK START: {}'.format(datetime.now()))
        logging.error('\n')
        for row in rows:
            odk_etag = uuid_parser(row.get('rowETag'))
            odk_id = uuid_parser(row.get('id'))
            savepoint_column_type = row.get('savepointType', 'INCOMPLETE')
            deleted = row.get('deleted', True)
            user_email = row.get('createUser', None)
            odk_extra_data = {
                'create_user': user_email,
                'last_update_user': row.get('lastUpdateUser', None),
                'locale': row.get('locale', None),
                'savepoint_timestamp': row.get('savepointTimestamp', None),
                'savepoint_creator': row.get('savepointCreator', None),
                'filterScope': row.get('filterScope', None)
            }
            logging.error('Processing odk_id {} with odk_etag {} START'.format(odk_id, odk_etag))
            if savepoint_column_type.lower() == 'complete' and deleted != 'true':
                save_or_update_project(row, user_email, odk_etag, odk_id, odk_extra_data, interoperability_links)
            else:
                logging.error('Incomplete or deleted: nothing to do')
            logging.error('\n')
        logging.error('ODK IMPORT TASK END: {}'.format(datetime.now()))

    # with open('project/static-json/odk.json') as odk_file:
    #     rows = json.load(odk_file)
    #     start_sync(rows, interoperability_links)
    start_sync(res.json(), interoperability_links)
