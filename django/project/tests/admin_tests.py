import mock
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template.response import TemplateResponse
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User, Permission
from rest_framework import status

from country.models import Country
from project.admin import ProjectAdmin, DigitalStrategyAdmin, TechnologyPlatformAdmin, PortfolioAdmin
from .factories.project_factories import ProjectBuilder
from project.resources import ProjectResource
from user.models import UserProfile
from project.models import Project, DigitalStrategy, TechnologyPlatform, Portfolio, ProjectVersion

from project.tests.setup import MockRequest
from core.utils import make_admin_list


class TestAdmin(TestCase):
    def setUp(self):
        super(TestAdmin, self).setUp()
        self.request = MockRequest()
        self.site = AdminSite()
        self.user = User.objects.create_user(username="alma", password="korte")
        self.userprofile = UserProfile.objects.create(user=self.user, name="almakorte")

        url = reverse('rest_register')
        data = {'email': 'test_user@gmail.com',
                'password1': '123456hetNYOLC',
                'password2': '123456hetNYOLC'}
        self.client.post(url, data)

    def test_admin(self):
        admin = DigitalStrategyAdmin(DigitalStrategy, self.site)
        self.assertEqual(admin.get_queryset(self.request).count(), DigitalStrategy.all_objects.all().count())
        translate_bools = ['is_translated_{}'.format(language_code) for language_code, _ in settings.LANGUAGES]
        self.assertEqual(admin.get_list_display(self.request), ['__str__', 'is_active'] + translate_bools)
        admin.list_display = ['__str__', 'is_active']
        self.assertEqual(admin.get_list_display(self.request), ['__str__', 'is_active'])

    def xtest_created_notification(self):  # pragma: no cover
        initial_email_count = len(mail.outbox)
        user_2 = User.objects.create_superuser(username='test_2', email='test2@test.test', password='a')
        UserProfile.objects.create(user=user_2, language='fr')

        tpa = TechnologyPlatformAdmin(TechnologyPlatform, self.site)

        ModelForm = tpa.get_form(self.request)
        data = {'name': 'New technology platform',
                'is_active': True}
        form = ModelForm(data)

        self.assertTrue(form.is_valid(), form.errors)
        tpa.save_form(self.request, form, False)

        self.assertEqual(len(mail.outbox),
                         initial_email_count + UserProfile.objects.all().count())

        first_en = '<meta http-equiv="content-language" content="en">' in mail.outbox[-2].message().as_string()
        en_index = -2 if first_en else -1
        fr_index = -1 if first_en else -2

        outgoing_en_email_text = mail.outbox[en_index].message().as_string()

        self.assertIn('New technology platform was created: {}'.format(str(form.instance)), outgoing_en_email_text)
        self.assertIn('<meta http-equiv="content-language" content="en">', outgoing_en_email_text)

        outgoing_fr_email_text = mail.outbox[fr_index].message().as_string()
        self.assertIn('<meta http-equiv="content-language" content="fr">', outgoing_fr_email_text)

    def xtest_modified_notification(self):  # pragma: no cover
        initial_email_count = len(mail.outbox)
        user_2 = User.objects.create_superuser(username='test_2', email='test2@test.test', password='a')
        UserProfile.objects.create(user=user_2, language='fr')

        tpa = TechnologyPlatformAdmin(TechnologyPlatform, self.site)
        technology_platform = TechnologyPlatform(name='Test platform')

        ModelForm = tpa.get_form(self.request, technology_platform)
        data = {'name': 'something different',
                'is_active': technology_platform.is_active}
        form = ModelForm(data, instance=technology_platform)

        self.assertTrue(form.is_valid(), form.errors)
        tpa.save_form(self.request, form, True)

        self.assertEqual(len(mail.outbox),
                         initial_email_count + UserProfile.objects.all().count())

        first_en = '<meta http-equiv="content-language" content="en">' in mail.outbox[-2].message().as_string()
        en_index = -2 if first_en else -1
        fr_index = -1 if first_en else -2

        outgoing_en_email_text = mail.outbox[en_index].message().as_string()

        self.assertIn('Technology Platform - {} was changed'.format(str(form.instance)), outgoing_en_email_text)
        self.assertIn('<meta http-equiv="content-language" content="en">', outgoing_en_email_text)

        outgoing_fr_email_text = mail.outbox[fr_index].message().as_string()
        self.assertIn('<meta http-equiv="content-language" content="fr">', outgoing_fr_email_text)

    def test_modified_but_not_changed(self):
        initial_email_count = len(mail.outbox)

        tpa = TechnologyPlatformAdmin(TechnologyPlatform, self.site)
        technology_platform = TechnologyPlatform(name='Test platform')

        ModelForm = tpa.get_form(self.request, technology_platform)
        data = {'name': technology_platform.name,
                'name_en': technology_platform.name,
                'is_active': technology_platform.is_active,
                'state': TechnologyPlatform.APPROVED}
        form = ModelForm(data, instance=technology_platform)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.has_changed(), form.changed_data)
        tpa.save_form(self.request, form, True)

        self.assertEqual(len(mail.outbox), initial_email_count)

    def test_project_admin_custom_fields(self):
        pa = ProjectAdmin(Project, self.site)
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.request.user = self.user

        p = Project.objects.create(name="test change view", draft=dict(country=Country.objects.get(id=1).id))
        p.team.add(self.userprofile.id)

        self.assertEqual(pa.get_country(p), Country.objects.get(id=1))
        self.assertEqual(pa.get_team(p), str(self.userprofile))
        self.assertFalse(pa.get_published(p))
        self.assertFalse(pa.has_add_permission(self.request))

    def test_project_admin_changeform_view(self):
        request = MockRequest()
        request.method = 'GET'
        request.POST = {}
        request.META = {'SCRIPT_NAME': 'from_test'}
        request.resolver_match = False

        content_type = ContentType.objects.get(app_label=Project._meta.app_label,
                                               model=Project._meta.model_name)
        change_permission = Permission.objects.get(content_type=content_type,
                                                   codename='change_{}'.format(Project._meta.model_name))

        p = Project.objects.create(name="test change view")
        self.user.user_permissions.add(change_permission)
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        request.user = self.user
        pa = ProjectAdmin(Project, self.site)
        response = pa.changeform_view(request, object_id=str(p.id))
        self.assertTrue(isinstance(response, TemplateResponse))

    def test_portfolio_admin_custom_fields(self):
        pa = PortfolioAdmin(Portfolio, self.site)
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.request.user = self.user
        self.userprofile.global_portfolio_owner = True
        self.userprofile.save()

        po = Portfolio.objects.create(name="test portfolio", description="test description")
        po.managers.set([self.userprofile])

        self.assertEqual(pa.managers_list(po), make_admin_list(po.managers.all()))

    @mock.patch('project.tasks.notify_user_about_approval.apply_async', return_value=None)
    def test_software_approve_in_admin(self, notify_user_about_approval):
        client = Client()

        password = '1234'
        admin = User.objects.create_superuser(username='test_2', email='test2@test.test', password=password)
        UserProfile.objects.create(user=admin)

        software = TechnologyPlatform.objects.create(name='test platform 20000', state=TechnologyPlatform.PENDING)

        change_url = reverse('admin:project_technologyplatform_changelist')
        data = {
            'action': 'approve',
            '_selected_action': [software.pk],
        }
        login_status = client.login(username=admin.email, password=password)
        response = client.post(change_url, data, follow=True)
        self.assertTrue(login_status)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        software.refresh_from_db()
        self.assertEqual(software.state, TechnologyPlatform.APPROVED)

        notify_user_about_approval.assert_called_once_with(args=('approve', software._meta.model_name, software.pk))

    @mock.patch('project.tasks.notify_user_about_approval.apply_async', return_value=None)
    def test_software_decline_in_admin(self, notify_user_about_approval):
        client = Client()

        password = '1234'
        admin = User.objects.create_superuser(username='test_2', email='test2@test.test', password=password)
        UserProfile.objects.create(user=admin)

        software = TechnologyPlatform.objects.create(name='test platform 20000', state=TechnologyPlatform.PENDING)

        change_url = reverse('admin:project_technologyplatform_changelist')
        data = {
            'action': 'decline',
            '_selected_action': [software.pk],
        }
        login_status = client.login(username=admin.email, password=password)
        response = client.post(change_url, data, follow=True)
        self.assertTrue(login_status)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        software.refresh_from_db()
        self.assertEqual(software.state, TechnologyPlatform.DECLINED)

        notify_user_about_approval.assert_called_once_with(args=('decline', software._meta.model_name, software.pk))

    def test_project_admin_version(self):
        """
        Basically an edge-case test since we're using a brand new project which was not made through API
        """
        pa = ProjectAdmin(Project, AdminSite())
        p = Project.objects.create(name="test link")
        p.team.add(self.userprofile.id)
        self.assertEqual(pa.versions(p), 0)
        self.assertEqual(pa.versions_detailed(p), '')
        ProjectVersion.objects.create(project=p, data=p.draft, name=p.name,
                                      user=p.team.first())

        self.assertEqual(pa.versions(p), 1)
        self.assertEqual(pa.versions_detailed(p)[-15:], 'Initial version')

        p.name = 'New name'
        p.save()
        ProjectVersion.objects.create(project=p, data=p.draft, name=p.name,
                                      user=p.team.first())

        self.assertEqual(pa.versions(p), 2)
        self.assertEqual(pa.versions_detailed(p)[-16:], 'name was changed')


    def test_missing_attributes_does_not_crash_export(self):
            """
            Test exporting a known set of projects using the ProjectResource.
            """

            project1 = ProjectBuilder().published(False).create(name="Project Alpha Alpha")

            draft_data = project1.draft

            # Remove two required attributes from the draft data
            # Pull this into a helper next time we need it in a test
            if 'unicef_leading_sector' in draft_data:
                del draft_data['unicef_leading_sector']
            if 'unicef_supporting_sectors' in draft_data:
                del draft_data['unicef_supporting_sectors']
            project1.draft = draft_data
            project1.save()

            resource = ProjectResource()

            # Query the projects to export
            queryset = Project.objects.filter(pk=project1.pk)

            # Export the queryset to CSV
            dataset = resource.export(queryset)
            exported_csv = dataset.csv

                # Split CSV into lines for processing
            csv_lines = exported_csv.strip().split("\n")

            # Extract headers and data rows
            headers = csv_lines[0].split(",")
            data_row = csv_lines[1].split(",")

            # Assert that the 'Lead Sector' and 'Supporting Sectors' columns are present
            self.assertIn('Lead Sector', headers)
            self.assertIn('Supporting Sectors', headers)

            # Find indices of the relevant columns
            lead_sector_index = headers.index('Lead Sector')
            supporting_sectors_index = headers.index('Supporting Sectors')

            # Assert that their values for project1 are empty
            self.assertEqual(data_row[lead_sector_index], "")
            self.assertEqual(data_row[supporting_sectors_index], "")