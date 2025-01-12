<template>
  <div class="DHAHelpCenter">
    <div class="PageTitle">
      <h2>Release history</h2>
    </div>

    <el-card class="HelpCard">
      <h3 id="4.0.0">INVENT 4.0.1</h3>
      <p>Deployed: 2025-01-07</p>
      <h4>Bug fixes</h4>
      <ul>
        <li>
          Fixed a bug that (incorrectly) informed users that help widget form submissions were unsuccessful. Bonus:
          added the page on which the user submitted the form to the metadata, providing additional context when
          analysing help requests.
        </li>
        <li>
          Fixed a bug where discontinued, completed or deleted initiatives incorrectly generated notifications prompting
          users to keep them up to date
        </li>
      </ul>
      <h4>Goal areas and Result areas</h4>
      <ul>
        <li>Updated Goal Areas and Result Areas to reflect the current Strategic Plan</li>
      </ul>
      <h4>Portfolio reviews</h4>
      <ul>
        <li>Deactivated reminder notifications for the deprecated Portfolio Review functionality</li>
      </ul>
      <h4>Administration</h4>
      <ul>
        <li>
          Added configuration option to reduce spam by sending all new taxonomy requests (software, hardware,... ) to
          INVENT team email address instead of all superusers
        </li>
      </ul>
      <hr />
      <h3 id="4.0.0">INVENT 4.0.0</h3>
      <p>Deployed: 2023-09-27</p>
      <h4>Technical updates</h4>
      <ul>
        <li>Upgrade technical components improve INVENT stability and security.</li>
        <li>Upgrade Django to v4.2.3</li>
        <li>Update supporting libraries</li>
        <li>Replace legacy authentication system</li>
        <li>Upgrade Postgres to v14</li>
      </ul>
      <hr />

      <h3 id="3.9.0">INVENT 3.9.0</h3>
      <p>Deployed: 2023-09-14</p>
      <h4>Country Office boards</h4>
      <ul>
        <li>Display UNICEF office name on initiative cards</li>
      </ul>
      <h4>Dataviz</h4>
      <ul>
        <li>
          Allow admins to set the latitude and longitude of UNICEF offices. This will allow dataviz e.g., Magasin, to
          position initiatives more precisely on a map
        </li>
      </ul>
      <h4>Solutions</h4>
      <ul>
        <li>
          Allow a solution to be tagged with a funding source of Set Aside 2021 or Set Aside 2022. This will support
          analysis
        </li>
      </ul>
      <h4>Other</h4>
      <ul>
        <li>Minor email wording tweaks</li>
        <li>Improved application performance monitoring</li>
        <li>Fix a bug due to duplicate user entries</li>
      </ul>
      <hr />

      <h3 id="3.8.0">INVENT 3.8.0</h3>
      <p>Deployed: 2023-09-11</p>
      <h4>Allow users to delete initiatives</h4>
      <ul>
        <li>Users can now delete any initiative that they are able to edit.</li>
      </ul>
      <h4>Notify users when their taxonomy requests are approved or declined</h4>
      <p>
        Users have always been able to request new entries in the taxonomy fields in the Technology section when
        creating/editing an initiative, allowing administrators to approve or decline these requests. This release
        enhances this workflow by providing feedback to users who have made such requests.
      </p>
      <ul>
        <li>
          Inform users when an administrator approves or declines their request for a new taxonomy tag in the Technology
          section of the form
        </li>
        <li>
          Allow administrators to add a comment when approving/declining a request, and display this comment in the
          notification email to the user
        </li>
      </ul>
      <h4>Technology playbook integration</h4>
      <p>
        To support the soft integration between INVENT and the Technology Playbook, this release adds a link to each
        phase on the create/edit initiative form, allowing users to consult the relevant content of the Playbook.
      </p>
      <ul>
        <li>
          Allow administrators to define a url for each phase. If this url is provided, a Learn more link will be
          displayed when to users when they expand the phase description.
        </li>
      </ul>
      <h4>Solutions</h4>
      <p>
        The notion of a solution previously existed in INVENT to model the solutions in the innovation portfolios. This
        has now been generalised to support work that is not in an innovation portfolio.
      </p>
      <ul>
        <li>Allow solutions to exist outside of portfolios</li>
        <li>Move Solutions from under portfolios/innovation/solutions to top level of site hierarchy</li>
      </ul>
      <h4>Other</h4>
      <ul>
        <li>Improve email template (e.g., cosmetic changes, fix broken / incorrect links,…)</li>
        <li>
          Improve synchronisation of INVENT's user list (displayed when you add a team member) with UNICEF's directory
          (technical improvement)
        </li>
        <li>Improve management of translation texts during deployments (technical improvement)</li>
      </ul>
      <hr />

      <h3 id="3.7.0">INVENT 3.7.0</h3>
      <p>Deployed: 2023-08-11</p>
      <h4>Improved country office page.</h4>
      <p>Introducing the new Country Office board!</p>
      <p>
        This board allows anyone to see the status of a CO's initiatives, by sector, including a highlight of those
        initiatives that have not changed phase in over 6 months.
      </p>
      <ul>
        <li>Guide shared separately</li>
      </ul>
      <h4>Admin</h4>
      <p>
        Improve configuration of initiative phases to allow an admin to select which phases represent the end of active
        work on an initiative. Currently set as Handover and Complete and Discontinued. This will allow INVENT to adapt
        to changes in underlying processes.
      </p>
      <h4>Breadcrumbs</h4>
      <p>
        Improve UX when viewing initiatives by using Initiatives as the breadcrumbs text instead of My initiatives.
        (Unfortunately, for technical reasons, this value is shared, so this change fixes most page views (in the
        inventory) but means that the My initiatives page shows Initiatives and links to the Inventory)
      </p>
      <hr />

      <h3 id="3.6.1">INVENT 3.6.1</h3>
      <p>Deployed: 2023-08-04</p>
      <h4>Admin</h4>
      <p>
        Improve admin user export (prevent timeout on larger exports, include job title and section where available)
      </p>
      <h4>API</h4>
      <ul>
        <li>Allow clients to retrieve unpublished initiatives</li>
      </ul>
      <h4>Fixes</h4>
      <ul>
        <li>Fix inconsistent history for initiatives published before November 2021</li>
      </ul>
      <hr />

      <h3 id="3.5.1">INVENT 3.5.1</h3>
      <p>Deployed: 2023-07-13</p>
      <h4>Bug fixes</h4>
      <ul>
        <li>Some last updated dates were incorrectly displayed</li>
        <li>Initiatives sometimes momentarily display incorrect/cached information (under investigation)</li>
        <li>Focal point contact details sometimes missing from initiative header section</li>
      </ul>
      <hr />

      <h3 id="3.5.0">INVENT v3.5.0</h3>
      <p>Deployed: 2023-07-11</p>
      <h4>Initiative management - Lead and supporting sectors</h4>
      <ul>
        <li>Split sector field into a required Lead sector and optional Supporting sectors fields.</li>
        <li>Use the new Lead sector and Supporting sectors fields in display and exports.</li>
      </ul>
      <p>Note: one single sector search field searches across all of the initiative's sectors, lead and supporting</p>
      <p>Improvements to focal point selection UX</p>
      <h4>Performance improvements</h4>
      <ul>
        <li>Reducing first load time for homepage and inventory page</li>
      </ul>
      <h4>Bug fixes</h4>
      <ul>
        <li>Timeout error on admin pages</li>
        <li>Horizontal scroll bars in all search fields in Firefox</li>
        <li>Security fix on exposed projects endpoint</li>
      </ul>
      <h4>Other</h4>
      <ul>
        <li>Use same (smaller) logo everywhere</li>
      </ul>
      <hr />

      <h3 id="3.4.0">INVENT v3.4.0</h3>
      <p>Deployed: 2023-05-31</p>
      <h4>Initiative management</h4>
      <ul>
        <li>
          Allow team members to be chosen from all UNICEF colleagues. Until this update you could only add a user if
          they had previously signed into INVENT.
        </li>
        <li>
          Select a user as a focal point. In previous versions users has to type a name and an email address. This
          didn't allow any kind of autocompletion, and created bugs when the email address didn't match a UNICEF
          account, etc.
        </li>
        <li>Display job title and section (where available) when choosing team members</li>
      </ul>
      <h4>Innovation Portfolios</h4>
      <ul>
        <li>Display portfolios of solutions, not initiatives.</li>
        <li>Allow portfolio managers to update portfolio metrics (cumulative funding, etc).</li>
      </ul>
      <h4>Bug fixes</h4>
      <ul>
        <li>Fix bug that resulted in incomplete exports</li>
        <li>Fix bug that prevented users from being redirected to the homepage after login</li>
        <li>Fix bug that showed incorrect dates to some users</li>
        <li>Fix bug that showed blank user names, making it impossible to add those users as team members</li>
        <li>Fix bug that prevented some links from being clickable</li>
        <li>Fix bug that generated duplicates of a draft initiative</li>
        <li>Fix bug that resulted in some initiatives not appearing on the map</li>
      </ul>
      <h4>Minor UI fixes</h4>
      <ul>
        <li>Remove footer</li>
        <li>Remove redundant "Organisation: UNICEF" field</li>
        <li>Allow access to portfolio edit from the portfolio page</li>
      </ul>
      <h4>Other</h4>
      <ul>
        <li>Improve API for Magasin integration</li>
        <li>Essential security improvements</li>
      </ul>
      <hr />

      <h3>INVENT Migration</h3>
      <p>Performed: 2023-05-04</p>
      <p>
        INVENT was migrated to a UNICEF-standard hosting setup to improve reliability and scalability and UNICEF's
        ability to support developers.
      </p>
      <hr />

      <h3 id="3.3.1">INVENT v3.3.1</h3>
      <p>Deployed: 2022-06-01</p>
      <ul>
        <li>Innovation Performance Portal improvements for Windows users who have activated text scaling</li>
        <li>Improved developer-facing documentation</li>
      </ul>
      <hr />

      <h3 id="3.1.23">INVENT v3.1.23</h3>
      <p>Deployed: 2022-04-11</p>
      <ul>
        <li>Innovation Performance Portal embed mechanism added but not exposed</li>
      </ul>
      <hr />

      <h3 id="3.1.6">INVENT v3.1.6</h3>
      <p>Deployed: 2022-03-22</p>
      <ul>
        <li>API changes for Innovation Performance indicators</li>
      </ul>
      <hr />

      <h3 id="3.1.6">INVENT v3.1.6</h3>
      <p>Deployed: 2022-03-11</p>
      <ul>
        <li>
          Admins can now generate larger initiative exports asynchronously. This avoids the timeout that prevented
          exports of large sets of initiatives.
        </li>
      </ul>
      <hr />

      <h3 id="3.1.3">INVENT v3.1.3</h3>
      <p>Deployed: 2022-03-11</p>
      <ul>
        <li>Bug fix: Initiatives list now appears again on home page and country page maps</li>
      </ul>
      <hr />

      <h3 id="3.1.1">INVENT v3.1.1</h3>
      <p>Deployed: 2022-03-10</p>

      <p>Maintenance release with enhanced API for future data visualizations</p>
      <h4>Minor bug fixes:</h4>
      <ul>
        <li>Safari layout</li>
        <li>End dates no longer default to 01-01-1970</li>
        <li>DHA logo no longer appears on some pages</li>
        <li>Translation engine fixes</li>
        <li>Problem statements now appear correctly in portfolio manager exports</li>
      </ul>
      <hr />

      <h3 id="2.9.6">INVENT v2.9.6</h3>
      <p>Deployed: 2022-02-02</p>
      <ul>
        <li>
          Lists of initiatives now include a column called Current phase that indicates the inferred current phase. The
          inferred current phase of an initiative is determined as follows:
        </li>
        <li>
          If no phase is marked as completed, then the current phase is the first phase (Opportunity and Ideation)
        </li>
        <li>
          If the last completed phase is Handover or Completed or Discontinued then this phase is retained as the
          current phase, as it is an end state for an initiative.
        </li>
        <li>
          In all other cases, the current phase is set to the phase immediately following the last completed phase.
        </li>
        <li>The multi-select Current phase filter filters on the new Current phase field.</li>
        <li>Exports now include the Current phase column</li>
        <li>Fixed a bug that sometimes prevented accessing a published initiative directly via saved/shared URL</li>
        <li>Other minor bug fixes and improvements</li>
      </ul>
      <hr />

      <h3 id="2.9.4">INVENT v2.9.4</h3>
      <p>Deployed: 2022-01-05</p>
      <ul>
        <li>
          Country managers can now export the list of initiatives for which they are an INVENT country focal point
        </li>
        <li>
          Some initiatives showed erroneous predicted end dates as the 01-01-1970. These have been removed, and the bug
          that caused this date to appear has been fixed
        </li>
        <li>
          An error that caused the export of some EAPRO initiatives to fail has been fixed (cause: special characters in
          text fields, possibly due to an import glitch)
        </li>
        <li>Minor bug fixes and improvements</li>
      </ul>
      <hr />

      <h3 id="2.8.4">INVENT v2.8.4</h3>
      <p>Deployed: 2021-11-09</p>
      <h4>Country manager</h4>
      <ul>
        <li>
          Super admins can now designate country managers who automatically have read/write permissions for all
          initiatives based in a country office in their area
        </li>
      </ul>
      <h4>Home page</h4>
      <ul>
        <li>The current user's initiatives and/or recently updated initiatives are shown above the map</li>
        <li>Featured initiatives can be defined by super admins and are shown on the homepage</li>
        <li>
          A cover photo can be defined for each initiative, and will be shown on the homepage card views of that
          initiative (My initiative, recently updated initiatives, featured initiatives)
        </li>
        <li>Home page visual design improvements</li>
      </ul>
      <h4>Minor improvements</h4>
      <ul>
        <li>
          Added pagination to the lists under My Initiatives (will fix timeout for those with many initiatives,
          favorites, ...)
        </li>
        <li>Removed redundant handshake and investor icons and labels</li>
        <li>Format numbers according to language preference</li>
        <li>Optimized text search performance</li>
        <li>Made number of initiatives per page setting global (applies wherever lists are paginated)</li>
        <li>
          All support requests via the widget are now sent to invent@unicef.org and subsequently to the ticket tracking
          system to ensure that the correct admin can respond
        </li>
      </ul>
      <hr />

      <h3 id="2.4.6">INVENT v2.4.6</h3>
      <p>Deployed: 2021-08-24</p>
      <h4>Portfolios - Review process</h4>
      <ul>
        <li>Reviewers can add a summary to their review</li>
        <li>Portfolio managers can add a summary to overall scoring</li>
      </ul>
      <h4>Product intelligence</h4>
      <ul>
        <li>Added basic Matomo tracking to understand user behavior</li>
        <li>Superadmins can now export user data in the admin interface</li>
      </ul>
      <h4>Inventory view</h4>
      <ul>
        <li>Added Innovation Categories to table and export</li>
      </ul>
      <h4>Other</h4>
      <ul>
        <li>Various fixes and improvements</li>
      </ul>
      <hr />

      <h3 id="2.3.0">INVENT v2.3.0</h3>
      <p>Deployed: 2021-08-04</p>
      <h4>Portfolios - Review process</h4>
      <ul>
        <li>Portfolio managers can now export initiatives with scoring and review data</li>
        <li>Reviewers can save their reviews as draft in order to work on them over multiple sessions</li>
        <li>
          Portfolio managers can move initiatives out of the review stage back into the inventory without losing the
          associated review data.
        </li>
        <li>Portfolio managers can remove reviewers and the associated review data from an initiative</li>
      </ul>
      <h4>Super admin viewing & exporting initiatives</h4>
      <ul>
        <li>Superadmins can now search initiatives in the admin interface</li>
        <li>Superadmins can now export initiative data in the admin interface</li>
      </ul>
      <h4>Inventory view</h4>
      <ul>
        <li>
          Navigating to a search URL will now open the search results page, allowing URLs to be shared or saved for
          later use. This also means clicking the back button on an initiative page will return to the inventory view
          without losing any search criteria.
        </li>
        <li>Only fields selected for display in the inventory table (using the gear icon) are now exported</li>
        <li>
          It's now possible to open initiatives in a new browser tab using the standard link behavior (right click, open
          in new tab, or ctrl-click/cmd-click)
        </li>
      </ul>
      <h4>New initiative</h4>
      <ul>
        <li>
          The person added as the focal point for an initiative is now automatically added to list of initiative
          editors.
        </li>
      </ul>
    </el-card>
  </div>
</template>

<script>
export default {
  methods: {
    goBack() {
      this.$router.go(-1)
    },
  },
}
</script>

<style lang="less">
@import '~assets/style/variables.less';
@import '~assets/style/mixins.less';

.DHAHelpCenter {
  .HelpCard {
    width: @cardSizeMedium;
    margin: 0 auto 80px;
  }
  hr {
    margin: 40px 0;
  }
}
</style>
