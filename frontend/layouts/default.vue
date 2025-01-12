<template>
  <div :class="layoutClass">
    <dialogs-container />
    <top-bar :auth="isAuthPage" />
    <action-bar v-if="showActionBar" />
    <nuxt />
    <django-feedback />
  </div>
</template>

<script>
import HeadMixin from '@/layouts/HeadMixin'
import TopBar from '@/components/common/TopBar.vue'
import ActionBar from '@/components/common/ActionBar.vue'
import DialogsContainer from '@/components/dialogs/DialogsContainer.vue'
import DjangoFeedback from '@/components/DjangoFeedback.vue'

export default {
  components: {
    TopBar,
    ActionBar,
    DialogsContainer,
    DjangoFeedback,
  },
  mixins: [HeadMixin],
  middleware: 'permissions',
  computed: {
    pureRoute() {
      if (this.$route && this.$route.name) {
        return this.$route.name.split('___')[0]
      }
      return null
    },
    isAuthPage() {
      return this.pureRoute === 'auth'
    },
    showActionBar() {
      const hiddenOn = [
        'index-login',
        'index-signup',
        'auth',
        'organisation-reset-key',
        'organisation',
        'organisation-innovation-performance',
      ]
      if (this.$route && this.$route.name) {
        return !hiddenOn.includes(this.pureRoute)
      }
      return false
    },
    layoutClass() {
      if (
        !['organisation', 'auth', 'organisation-login', 'organisation-signup', 'organisation-reset-key'].includes(
          this.pureRoute
        )
      ) {
        return 'SubPage'
      } else if (this.$route.params.organisation !== '-') {
        return 'CountryDonorLandingPage'
      }
      return 'LandingPage'
    },
  },
}
</script>

<style lang="less">
@import '~assets/style/variables.less';
@import '~assets/style/mixins.less';

.LandingPage {
}

.CountryDonorLandingPage {
  .TopBar {
    .TopBarInner {
      height: @topBarHeightSubpage;

      .LogoHolder {
        .LogoWHO,
        .Separator {
          display: none;
        }
      }
    }
  }
}

.SubPage {
  .TopBar {
    .TopBarInner {
      height: @topBarHeightSubpage;

      .LogoHolder {
        .LogoWHO,
        .Separator {
          display: none;
        }
      }
    }
  }
}
</style>
