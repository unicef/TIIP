<template>
  <div class="breadcrumb">
    <p v-for="breadcrumb in breadcrumbs" :key="breadcrumb.id">
      <nuxt-link :to="localePath(breadcrumb.localePath)" :disabled="!breadcrumb.name">
        <fa v-if="breadcrumb.id === 'organisation'" icon="home" />
        <template v-else>
          <fa icon="angle-right" size="sm" />
          {{ idToName(breadcrumb.localePath.name) }}
          {{ breadcrumb.text }}
        </template>
      </nuxt-link>
    </p>
  </div>
</template>

<script>
import split from 'lodash/split'
import join from 'lodash/join'

import { mapState, mapGetters } from 'vuex'

export default {
  data() {
    return {
      organisation: this.$gettext('Organisation'),
      'organisation-login': this.$gettext('Login'),
      'organisation-signup': this.$gettext('Signup'),
      'organisation-reset-key': this.$gettext('Reset'),
      'organisation-portfolio-innovation': this.$gettext('Innovation Portfolios'),
      'organisation-solutions': this.$gettext('Solutions'),
      'organisation-solutions-id-edit': this.$gettext('Edit solution'),
      'organisation-solutions-create': this.$gettext('Create new solution'),
      'organisation-portfolio-management': this.$gettext('Portfolio Manager'),
      'organisation-initiatives': this.$gettext('Initiatives'),
      'organisation-portfolio-management-new': this.$gettext('New portfolio'),
      'organisation-portfolio-management-id-edit': this.$gettext('Edit portfolio'),
      'organisation-initiatives-create': this.$gettext('New Initiative'),
      'organisation-initiatives-id-published': this.$gettext('Published Initiative'),
      'organisation-initiatives-id-edit': this.$gettext('Edit Initiative'),
      'organisation-initiatives-id-stages': this.$gettext('Phases'),
      'organisation-releases': this.$gettext('Release history'),

      // route exclutions
      exclude: [
        'organisation-inventory-list',
        'organisation-inventory',
        'organisation-edit-profile',
        'organisation-admin',
        'organisation-admin-country',
        'organisation-admin-donor',
        'organisation-admin-import',
        'organisation-admin-import-id',
        'organisation-email-confirmation',
      ],
    }
  },
  computed: {
    ...mapState({
      portfolioManagementName: (state) => state.portfolio.name,
      solutionName: (state) => state.solution.name,
    }),
    ...mapGetters({
      initiative: 'project/getProjectData',
      portfolioInnovationName: 'portfolio/getName',
      getPortfolios: 'solution/getPortfoliosList',
      draft: 'project/getProjectData',
      published: 'project/getPublished',
    }),
    pureRoute() {
      if (this.$route && this.$route.name) {
        return this.$route.name.split('___')[0]
      }
      return null
    },
    breadcrumbs() {
      let name = ''
      let breadcrumbs = []
      const route = this.exclude.includes(this.pureRoute) ? 'organisation' : this.pureRoute

      split(route, '-').forEach((item) => {
        name = name !== '' ? join([name, item], '-') : item
        if (name !== 'organisation-portfolio') {
          const path = this.$route.query.portfolio
          if (item === 'solutions' && path) {
            const portfolioName = this.getPortfolios.find((portfolio) => portfolio.id === path * 1).name

            breadcrumbs = [
              ...breadcrumbs,
              {
                id: item,
                localePath: {
                  name: `organisation-portfolio-innovation-id`,
                  params: { id: path },
                },
                text: portfolioName || '',
              },
            ]
          } else if (name === 'organisation-portfolio-innovation-id') {
            breadcrumbs = [
              ...breadcrumbs,
              {
                id: item,
                localePath: {
                  name: `organisation-portfolio-innovation-id`,
                  params: { id: this.$route.params.id },
                },
                text: this.portfolioInnovationName || '',
              },
            ]
          } else if (name === 'organisation-portfolio-innovation') {
            breadcrumbs = [
              ...breadcrumbs,
              {
                id: item,
                localePath: {
                  name,
                  params: { ...this.$route.params },
                },
                text: this[name] || '',
              },
            ]
          } else if (name === 'organisation-initiatives') {
            breadcrumbs = [
              ...breadcrumbs,
              {
                id: item,
                localePath: {
                  name: 'organisation-inventory-list',
                  params: { ...this.$route.params },
                },
                text: this.$gettext('Initiatives'),
              },
            ]
          } else {
            breadcrumbs = [
              ...breadcrumbs,
              {
                id: item,
                localePath: {
                  name,
                  params: { ...this.$route.params },
                  query: { ...this.$route.query },
                },
                text: this[name] || '',
              },
            ]
          }
        }
      })
      return breadcrumbs
    },
  },
  methods: {
    idToName(route) {
      switch (route) {
        case 'organisation-initiatives-id':
          return this.$route.name.includes('published') ? this.published.name : this.draft.name
        case 'organisation-solutions-id':
          return this.solutionName
        // case 'organisation-portfolio-innovation-id':
        //   return this.portfolioInnovationName
        case 'organisation-portfolio-management-id':
          return this.portfolioManagementName
        default:
          return ''
      }
    },
  },
}
</script>

<style lang="less" scoped>
@import '~assets/style/variables.less';

.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  height: inherit;
  color: @colorWhite;
  p {
    margin: 0 0 0 8px;
    a {
      text-decoration: none;
      transition: @transitionFade;
      font-size: @fontSizeBase;
      letter-spacing: 0;
      line-height: 18px;
      svg {
        margin-right: 8px;
      }
    }
  }
}
</style>
