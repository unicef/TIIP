import copy
from datetime import datetime, timedelta

from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from country.models import CountryCustomQuestion
from project.tests.setup import SetupTests
from project.models import ProjectVersion, Project
from user.tests import create_profile_for_user


class MockRequest:
    user = None
    GET = {}
    COOKIES = {}


class ProjectVersionTests(SetupTests):

    def setUp(self):
        super().setUp()

        self.project = Project.objects.get(id=self.project_id)
        versions = ProjectVersion.objects.filter(project__pk=self.project_id)
        self.assertEqual(len(versions), 2)
        version = versions[0]
        project = Project.objects.get(id=self.project_id)

        self.assertEqual(version.data, project.draft)
        self.assertEqual(version.name, project.name)
        self.assertEqual(version.version, 1)
        self.assertEqual(version.user, self.userprofile)

    def test_project_versioning(self):
        url = reverse("project-publish", kwargs={"project_id": self.project_id,
                                                 "country_office_id": self.country_office.id})
        versions = list(ProjectVersion.objects.filter(project__pk=self.project_id))
        self.assertEqual(len(versions), 2)

        version = versions[-1]
        project = Project.objects.get(id=self.project_id)

        self.assertEqual(version.data, project.data)
        self.assertEqual(version.name, project.name)
        self.assertEqual(version.version, 2)
        self.assertEqual(version.user, self.userprofile)

        # publish again with same data
        response = self.test_user_client.put(url, self.project_data, format="json")
        self.assertEqual(response.status_code, 200)

        versions = ProjectVersion.objects.filter(project__pk=self.project_id)
        self.assertEqual(len(versions), 2)
        updated_data = copy.deepcopy(self.project_data)
        updated_data['project']['name'] = 'Updated_project_name'

        # publish again with new data
        response = self.test_user_client.put(url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)

        versions = ProjectVersion.objects.filter(project__pk=self.project_id)
        self.assertEqual(len(versions), 3)
        version_1 = versions.filter(version=2)[0]
        version_2 = versions.filter(version=3)[0]
        self.assertEqual(version_1.data, project.data)
        self.assertEqual(version_1.name, project.name)
        project.refresh_from_db()
        self.assertEqual(version_2.data, project.data)
        self.assertEqual(version_2.name, project.name)
        self.assertNotEqual(version_1.data, version_2.data)

    def test_project_version_with_gaps(self):
        """
        Test that modifying or publishing a project creates a new version with the next available number,
        even if there are gaps in the version sequence.
        """

        # There are two versions of the project after setup
        versions = list(ProjectVersion.objects.filter(project__pk=self.project_id))
        self.assertEqual(len(versions), 2)

        # Manually create a gap by removing the first version. There is now only one version with version number= 2
        ProjectVersion.objects.filter(project=self.project, version=1).delete()

        # Publish the project with the updated data so there will be two versions
        updated_data = copy.deepcopy(self.project_data)
        updated_data['project']['name'] = 'Updated Project Name'
        publish_url = reverse("project-publish", kwargs={"project_id": self.project_id,
                                                        "country_office_id": self.country_office.id})
        response = self.test_user_client.put(publish_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)

        # Ensure the new version is created with the next available version number
        versions = ProjectVersion.objects.filter(project=self.project).order_by("version")
        self.assertEqual(len(versions), 2)
        self.assertEqual(list(versions.values_list("version", flat=True)), [2, 3,])

        # Check the data in the newly created version
        new_version = versions.get(version=3)
        self.assertEqual(new_version.name, updated_data['project']['name'])
        self.assertEqual(new_version.user, self.userprofile)

    def test_project_versions_history(self):
        new_data = copy.deepcopy(self.project_data)
        new_data['project']['name'] = new_data['project']['name'] + ' changed'
        new_data['project']['contact_name'] = new_data['project']['contact_name'] + ' changed'
        new_data['project']['health_focus_areas'] = [2, 3]
        new_data['project']['start_date'] = str(datetime.today().date() + timedelta(days=1))
        new_data['project']['links'] = [dict(link_type=0, link_url="https://website.com")]
        del new_data['project']['result_area']
        del new_data['project']['end_date']

        publish_url = reverse("project-publish", kwargs={"project_id": self.project_id,
                                                         "country_office_id": self.country_office.id})
        response = self.test_user_client.put(publish_url, new_data, format="json")
        self.assertEqual(response.status_code, 200)

        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)

        last_version = response.json()[-1]
        changes = last_version['changes']

        name_change = [ch for ch in changes if ch['field'] == 'name'][0]
        self.assertEqual(name_change['added'], new_data['project']['name'])
        self.assertEqual(name_change['removed'], self.project_data['project']['name'])

        contact_name_change = [ch for ch in changes if ch['field'] == 'contact_name'][0]
        self.assertEqual(contact_name_change['added'], new_data['project']['contact_name'])
        self.assertEqual(contact_name_change['removed'], self.project_data['project']['contact_name'])

        hfa_change = [ch for ch in changes if ch['field'] == 'health_focus_areas'][0]
        self.assertEqual(hfa_change['added'],
                         list(set(new_data['project']['health_focus_areas']) -
                              set(self.project_data['project']['health_focus_areas'])))
        self.assertEqual(hfa_change['removed'],
                         list(set(self.project_data['project']['health_focus_areas']) -
                              set(new_data['project']['health_focus_areas'])))

        start_date_change = [ch for ch in changes if ch['field'] == 'start_date'][0]
        self.assertEqual(start_date_change['added'], new_data['project']['start_date'])
        self.assertEqual(start_date_change['removed'], self.project_data['project']['start_date'])

        end_date_change = [ch for ch in changes if ch['field'] == 'end_date'][0]
        self.assertIsNone(end_date_change['added'])
        self.assertEqual(end_date_change['removed'], self.project_data['project']['end_date'])

        result_area_change = [ch for ch in changes if ch['field'] == 'result_area'][0]
        self.assertIsNone(result_area_change['added'])
        self.assertEqual(result_area_change['removed'], self.project_data['project']['result_area'])

        links_change = [ch for ch in changes if ch['field'] == 'links'][0]
        self.assertIsNone(links_change['added'])
        self.assertIsNone(links_change['removed'])
        self.assertTrue(links_change['special'])

        new_data['project']['result_area'] = 1
        response = self.test_user_client.put(publish_url, new_data, format="json")
        self.assertEqual(response.status_code, 200)

        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)

        last_version = response.json()[-1]
        changes = last_version['changes']

        result_area_change = [ch for ch in changes if ch['field'] == 'result_area'][0]
        self.assertEqual(result_area_change['added'], new_data['project']['result_area'])
        self.assertIsNone(result_area_change['removed'])
        self.assertFalse(result_area_change['special'])

    def test_project_history_public_view(self):
        new_data = copy.deepcopy(self.project_data)
        new_data['project']['name'] = new_data['project']['name'] + ' changed'

        publish_url = reverse("project-publish", kwargs={"project_id": self.project_id,
                                                         "country_office_id": self.country_office.id})
        draft_url = reverse("project-draft", kwargs={"project_id": self.project_id,
                                                     "country_office_id": self.country_office.id})
        response = self.test_user_client.put(draft_url, new_data, format="json")
        self.assertEqual(response.status_code, 200)

        # create a new user who is not a team member
        url = reverse("rest_register")
        data = {
            "email": "test_user_viewer@gmail.com",
            "password1": "123456hetNYOLC",
            "password2": "123456hetNYOLC"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201, response.json())
        create_profile_for_user(response)

        test_user_key = response.json().get("token")
        test_user_client = APIClient(HTTP_AUTHORIZATION="Token {}".format(test_user_key), format="json")

        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = test_user_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), ProjectVersion.objects.filter(project_id=self.project_id,
                                                                             published=True).count())

        # publish new version with one extra change
        new_data['project']['contact_name'] = new_data['project']['contact_name'] + ' changed'
        response = self.test_user_client.put(publish_url, new_data, format="json")
        self.assertEqual(response.status_code, 200)

        # public user should find only one extra version with the two changes that happened during the draft + publish
        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = test_user_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), ProjectVersion.objects.filter(project_id=self.project_id,
                                                                             published=True).count())

        last_version = response.json()[-1]
        changes = last_version['changes']
        name_change = [ch for ch in changes if ch['field'] == 'name'][0]
        self.assertEqual(name_change['added'], new_data['project']['name'])
        self.assertEqual(name_change['removed'], self.project_data['project']['name'])

        contact_name_change = [ch for ch in changes if ch['field'] == 'contact_name'][0]
        self.assertEqual(contact_name_change['added'], new_data['project']['contact_name'])
        self.assertEqual(contact_name_change['removed'], self.project_data['project']['contact_name'])

    def test_project_beyond_history_feature(self):
        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()[0]['beyond_history'])

        project = Project.objects.get(id=self.project_id)
        versions = project.versions.all()

        for v in versions:
            v.created = datetime(2021, 11, 9)
            v.save()

        project.created = datetime(2021, 10, 9)
        project.save()

        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()[0]['beyond_history'])

    def test_custom_questions_with_history(self):
        q1 = CountryCustomQuestion.objects.create(question="test private", country_id=self.country_id, private=True)
        q2 = CountryCustomQuestion.objects.create(question="test", country_id=self.country_id)
        q3 = CountryCustomQuestion.objects.create(question="test2 private", country_id=self.country_id, private=True)

        data = copy.deepcopy(self.project_data)
        data.update({"country_custom_answers": [dict(question_id=q1.id, answer=["private answer 1"]),
                                                dict(question_id=q2.id, answer=["public answer"]),
                                                dict(question_id=q3.id, answer=["private answer 2"])]})
        del data['project']['end_date']
        del data['project']['partners']

        publish_url = reverse("project-publish", kwargs={"project_id": self.project_id,
                                                         "country_office_id": self.country_office.id})
        response = self.test_user_client.put(publish_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        # publish new version with one extra change
        data.update({"country_custom_answers": [dict(question_id=q2.id, answer=["public answer changed"])]})
        data['project']['end_date'] = str(datetime.today().date())
        response = self.test_user_client.put(publish_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)

        last_version = response.json()[-1]
        changes = last_version['changes']
        custom_question_change = [ch for ch in changes if ch['field'] == 'country_custom_answers'][0]
        self.assertIsNone(custom_question_change['added'])
        self.assertIsNone(custom_question_change['removed'])
        self.assertTrue(custom_question_change['special'])

    def test_project_unpublished_state_on_history(self):
        url = reverse('project-unpublish', kwargs={'project_id': self.project_id})
        response = self.test_user_client.put(url, format='json')
        self.assertEqual(response.status_code, 200)

        url = reverse("project-versions-retrieve", kwargs={"pk": self.project_id})
        response = self.test_user_client.get(url)
        self.assertEqual(response.status_code, 200)

        last_version = response.json()[-1]
        self.assertTrue(last_version['was_unpublished'])
