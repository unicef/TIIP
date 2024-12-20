from import_export import resources
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from .models import Project, UNICEFSector, UNICEFGoal, InnovationCategory, CPD, Stage, TechnologyPlatform, \
    HardwarePlatform, NontechPlatform, ISC, PlatformFunction, UNICEFResultArea, InnovationWay, \
    ProblemStatement, Portfolio
from import_export.fields import Field
from django.utils.translation import gettext_lazy as _

from country.models import Country, CountryOffice, Currency
from .models import Solution

from project.serializers import LinkSerializer, PartnerSerializer


class SolutionsResource(resources.ModelResource):
    name = Field(column_name=_('Solution name'))
    portfolio_list = Field(column_name=_('Portfolios'))
    phase = Field(column_name=_('Phase'))
    open_source_frontier_tech = Field(
        column_name=_('Open source frontier tech'))
    learning_investment = Field(column_name=_('Learning investment'))
    people_reached = Field(column_name=_(
        'People reached [if empty -> sum of countries]'))
    list_of_countries = Field(column_name=_(
        'Countries [Country - Region - People reached]'))

    class Meta:
        model = Solution
        fields = ('name', 'portfolio_list', 'phase', 'open_source_frontier_tech',
                  'learning_investment', 'people_reached', 'list_of_countries',)
        export_order = ('name', 'portfolio_list', 'phase', 'open_source_frontier_tech',
                        'learning_investment', 'people_reached', 'list_of_countries',)

    def dehydrate_name(self, solution):  # pragma: no cover
        return solution.name

    def dehydrate_portfolio_list(self, solution):  # pragma: no cover
        return ", ".join([po.name for po in list(solution.portfolios.all())])

    def dehydrate_phase(self, solution):  # pragma: no cover
        return solution.phase

    def dehydrate_open_source_frontier_tech(self, solution):  # pragma: no cover
        return solution.open_source_frontier_tech

    def dehydrate_learning_investment(self, solution):  # pragma: no cover
        return solution.learning_investment

    def dehydrate_people_reached(self, solution):  # pragma: no cover
        return solution.people_reached

    def dehydrate_list_of_countries(self, solution):  # pragma: no cover
        countries_with_data = solution.countrysolution_set.all()
        countries_with_people_reached = ['{} - {} - {}'.format(cwd.country, CountryOffice.REGIONS[cwd.region][1],
                                                               cwd.people_reached) for cwd in countries_with_data]
        return ', '.join(countries_with_people_reached)


class PortfolioResource(resources.ModelResource):
    managers = Field(column_name=_('Managers of the portfolio'))
    id = Field(column_name=_('ID'))
    name = Field(column_name=_('Name'))
    description = Field(column_name=_('Description'))
    icon = Field(column_name=_('Icon'))
    status = Field(column_name=_('Status'))
    investment_to_date = Field(column_name=_('Investment to date'))
    innovation_hub = Field(column_name=_('Innovation Hub'))
    landscape_review = Field(column_name=_('Completed landscape review'))

    class Meta:
        model = Portfolio
        fields = ('id', 'name', 'description', 'icon',
                  'managers', 'status', 'investment_to_date', 'innovation_hub', 'landscape_review')
        export_order = ('id', 'name', 'description', 'managers', 'icon',
                        'status', 'investment_to_date', 'innovation_hub', 'landscape_review')

    def dehydrate_managers(self, portfolio):  # pragma: no cover
        return ', '.join([manager.user.email for manager in portfolio.managers.all()])

    def dehydrate_id(self, portfolio):  # pragma: no cover
        return portfolio.id

    def dehydrate_name(self, portfolio):  # pragma: no cover
        return portfolio.name

    def dehydrate_description(self, portfolio):  # pragma: no cover
        return portfolio.description

    def dehydrate_icon(self, portfolio):  # pragma: no cover
        return portfolio.icon

    def dehydrate_status(self, portfolio):  # pragma: no cover
        return portfolio.status

    def dehydrate_investment_to_date(self, portfolio):  # pragma: no cover
        return portfolio.investment_to_date

    def dehydrate_innovation_hub(self, portfolio):  # pragma: no cover
        return portfolio.innovation_hub

    def dehydrate_landscape_review(self, portfolio):  # pragma: no cover
        return portfolio.landscape_review


class ProblemStatementResource(resources.ModelResource):  # pragma: no cover
    portfolio_id = Field(column_name=_('Portfolio ID'))
    portfolio_name = Field(column_name=_('Portfolio Name'))
    id = Field(column_name=_('ID'))
    name = Field(column_name=_('Label'))
    description = Field(column_name=_('Narrative'))

    class Meta:
        model = ProblemStatement
        fields = ('id', 'name', 'portfolio_id',
                  'portfolio_name', 'description')
        export_order = ('portfolio_id', 'portfolio_name',
                        'id', 'name', 'description')

    def dehydrate_portfolio_id(self, problem_statement):
        portfolio_id = getattr(problem_statement.portfolio, 'id', '')
        return portfolio_id

    def dehydrate_portfolio_name(self, problem_statement):
        portfolio_name = getattr(problem_statement.portfolio, 'name', '')
        return portfolio_name

    def dehydrate_id(self, problem_statement):
        return problem_statement.id

    def dehydrate_name(self, problem_statement):
        return problem_statement.name

    def dehydrate_description(self, problem_statement):
        return problem_statement.description


class ProjectResource(resources.ModelResource):  # pragma: no cover
    """
    This class is basically a serializer for the django-import-export module
    TODO: write unit tests if necessary
    """
    # General Overview
    published = Field(column_name=_('Published'))
    contact = Field(column_name=_('Contact'))
    team = Field(column_name=_('Team'))
    overview = Field(column_name=_('Overview'))
    narrative = Field(column_name=_('Narrative'))
    country = Field(column_name=_('Country'))
    unicef_office = Field(column_name=_('UNICEF Office'))

    # Categorization
    unicef_leading_sector = Field(column_name=_('Lead Sector'))
    unicef_supporting_sectors = Field(column_name=_('Supporting Sectors'))
    goal_area = Field(column_name=_('Goal Area'))
    result_area = Field(column_name=_('Result Area'))
    innovations = Field(column_name=_('Innovation(s)'))
    innovation_categories = Field(column_name=_('Innovation category(ies)'))

    # Implementation Overview
    program_targets = Field(column_name=_('Program targets'))
    program_targets_achieved = Field(column_name=_('Program targets achieved'))
    beneficiaries_number = Field(
        column_name=_('Number of beneficiaries reached'))
    current_achievements = Field(column_name=_('Current achievements'))
    cpd = Field(column_name=_('Country Programme Document inclusion'))
    awp_note = Field(column_name=_('Outcome in Annual Work Plan'))
    wbs = Field(column_name=_('Work Breakdown Structure (WBS) number'))
    budget = Field(column_name=_('Budget'))
    total_budget_narrative = Field(
        column_name=_('Activities covered by budget'))
    funding_needs = Field(column_name=_('Funding gaps'))
    partnership_needs = Field(column_name=_('Partnership needs'))
    links = Field(column_name=_('Links'))

    # Completion of initiative phases (stages)
    stages = Field(column_name=_('Completion of initiative phases'))
    current_phase = Field(column_name=_('Current phase'))

    # Partners
    partners = Field(column_name=_('Partners'))

    # Technology
    software_platforms = Field(column_name=_('Software Platform(s)'))
    hardware_platforms = Field(column_name=_('Hardware Platform(s)'))
    nontech_platforms = Field(column_name=_('Non-technology Platform(s)'))
    platform_functions = Field(column_name=_('Platform functions'))
    isc = Field(column_name=_('Information security classification'))

    class Meta:
        model = Project
        fields = ('id', 'name', 'published', 'contact', 'team', 'modified')
        export_order = ('id', 'name', 'published', 'modified',
                        'contact', 'team', 'overview')

    def export_queryset(self, queryset, using_transactions=True, use_bulk=True, **kwargs):
        if use_bulk:
            return self.export_bulk(queryset, **kwargs)
        else:
            return super().export_queryset(queryset, using_transactions=using_transactions, **kwargs)

    def export_field(self, field, obj):
        data = super().export_field(field, obj)
        if isinstance(data, str):
            data = ILLEGAL_CHARACTERS_RE.sub('', data)
        return data

    def get_data_member(self, project):
        """
        shorthand for getting the data member
        """
        return project.data if project.public_id != '' else project.draft

    def dehydrate_published(self, project):
        return "True" if project.public_id != '' else "False"

    def dehydrate_contact(self, project):
        data = self.get_data_member(project)
        return f'{data.get("contact_name", "None")} <{data.get("contact_email", "None")}>'

    def dehydrate_team(self, project):
        return ", ".join([str(p) for p in project.team.all()])

    def dehydrate_overview(self, project):
        return self.get_data_member(project).get('overview', None)

    def dehydrate_narrative(self, project):
        return self.get_data_member(project).get('implementation_overview', None)

    def dehydrate_unicef_office(self, project):
        try:
            return CountryOffice.objects.get(id=self.get_data_member(project).get('country_office')).name
        except CountryOffice.DoesNotExist:
            return None

    def dehydrate_country(self, project):
        try:
            return Country.objects.get(id=self.get_data_member(project).get('country')).name
        except Country.DoesNotExist:
            return None

    def dehydrate_unicef_leading_sector(self, project):
        sector = self.get_data_member(project).get('unicef_leading_sector', [])
        qs = UNICEFSector.objects.filter(id__in=sector)
        return qs[0].name if qs.count() else None

    def dehydrate_unicef_supporting_sectors(self, project):
        sector = self.get_data_member(project).get('unicef_supporting_sectors', [])
        qs = UNICEFSector.objects.filter(id__in=sector)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_goal_area(self, project):
        try:
            return UNICEFGoal.objects.get(id=self.get_data_member(project).get('goal_area')).name
        except UNICEFGoal.DoesNotExist:
            return None

    def dehydrate_result_area(self, project):
        try:
            return UNICEFResultArea.objects.get(id=self.get_data_member(project).get('result_area')).name
        except UNICEFResultArea.DoesNotExist:
            return None

    def dehydrate_innovations(self, project):
        ids = self.get_data_member(project).get('innovation_ways')
        if ids:
            names = InnovationWay.objects.filter(id__in=self.get_data_member(project).get('innovation_ways')).\
                values_list('name', flat=True)
            return ', '.join(names) if names else None
        return None

    def dehydrate_innovation_categories(self, project):
        category = self.get_data_member(project).get('innovation_categories')
        qs = InnovationCategory.objects.filter(id__in=category)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_program_targets(self, project):
        return self.get_data_member(project).get('program_targets')

    def dehydrate_program_targets_achieved(self, project):
        return self.get_data_member(project).get('program_targets_achieved')

    def dehydrate_beneficiaries_number(self, project):
        return self.get_data_member(project).get('target_group_reached', 0)

    def dehydrate_current_achievements(self, project):
        return self.get_data_member(project).get('current_achievements')

    def dehydrate_cpd(self, project):
        cpd = self.get_data_member(project).get('cpd')
        try:
            return ', '.join(CPD.objects.filter(id__in=cpd).values_list('name', flat=True))
        except CPD.DoesNotExist:
            return None

    def dehydrate_awp_note(self, project):
        return self.get_data_member(project).get('awp')

    def dehydrate_wbs(self, project):
        wbs_list = self.get_data_member(project).get('wbs')
        return ", ".join(wbs for wbs in wbs_list) if wbs_list else None

    def dehydrate_budget(self, project):
        data = self.get_data_member(project)
        try:
            currency_code = Currency.objects.get(id=data.get('currency')).code
        except Currency.DoesNotExist:
            currency_code = ""
        budget = data['total_budget'] if 'total_budget' in data else 0
        return " ".join([str(budget), currency_code])

    def dehydrate_total_budget_narrative(self, project):
        return self.get_data_member(project).get('total_budget_narrative')

    def dehydrate_funding_needs(self, project):
        return self.get_data_member(project).get('funding_needs', 0)

    def dehydrate_partnership_needs(self, project):
        return self.get_data_member(project).get('partnership_needs')

    def dehydrate_links(self, project):
        links_list = self.get_data_member(project).get('links')
        link_types = {link[0]: link[1] for link in LinkSerializer.LINK_TYPE}
        link_types[''] = "unknown"
        links = []
        for link_data in links_list:
            l_type = link_types[link_data.get("link_type", "")]
            l_url = link_data.get('link_url', "unknown")
            links.append(f'{l_type}: {l_url}')
        return ', '.join(links) if links else None

    def dehydrate_stages(self, project):
        stages = []
        start_date = self.get_data_member(project).get('start_date')
        if start_date:
            stages.append(f'Start ({start_date})')
        stages_data = self.get_data_member(project).get('stages')
        if stages_data:
            for stage in stages_data:
                try:
                    stages.append(
                        f'{Stage.objects.get(id=stage["id"]).name} ({stage.get("date", "")})')
                except Stage.DoesNotExist:
                    continue
        end_date = self.get_data_member(project).get('end_date')
        if end_date:
            stages.append(f'End ({end_date})')
        return ', '.join(stages)

    def dehydrate_current_phase(self, project):
        stage_id = self.get_data_member(project).get('current_phase')
        try:
            return Stage.objects.get(id=stage_id).name
        except Exception:
            return 'No phase data'

    def dehydrate_partners(self, project):
        if 'partners' not in self.get_data_member(project):
            return None
        p_type_lookup = {p[0]: p[1] for p in PartnerSerializer.PARTNER_TYPE}
        partners = []
        for partner in self.get_data_member(project)['partners']:
            p_type = p_type_lookup[partner['partner_type']
                                   ] if 'partner_type' in partner else "n/a"
            p_string = f'{p_type}: {partner.get("partner_name")} ({partner.get("partner_contact")} - ' \
                       f'{partner.get("partner_email")} - {partner.get("partner_website")})'
            partners.append(p_string)
        return ', '.join(partners)

    def dehydrate_software_platforms(self, project):
        ids = self.get_data_member(project).get('platforms')
        if not ids:
            return None
        qs = TechnologyPlatform.objects.filter(id__in=ids)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_hardware_platforms(self, project):
        ids = self.get_data_member(project).get('hardware')
        if not ids:
            return None
        qs = HardwarePlatform.objects.filter(id__in=ids)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_nontech_platforms(self, project):
        ids = self.get_data_member(project).get('nontech')
        if not ids:
            return ""
        qs = NontechPlatform.objects.filter(id__in=ids)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_platform_functions(self, project):
        ids = self.get_data_member(project).get('functions')
        if not ids:
            return ""
        qs = PlatformFunction.objects.filter(id__in=ids)
        return ", ".join(res.name for res in qs) if qs.count() else None

    def dehydrate_isc(self, project):
        id = self.get_data_member(project).get('isc')
        if not id:
            return None
        try:
            return ISC.objects.get(id=id).name
        except ISC.DoesNotExist:
            return None
