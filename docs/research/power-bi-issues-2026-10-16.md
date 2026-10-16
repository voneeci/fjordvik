# Common problems with Microsoft Power BI: a sourced learning note

Prepared for Reece Venema (data and AI consultant, Helsinki) ahead of a Power BI role.
Research date: 16 October 2026. Every page cited below was opened and read on 16 October 2026 unless marked "not opened".

## How to read this note

Each item gives the problem in one plain sentence, why it matters to an organisation, the source (address, page date, exact quote), a label, and any mitigation a source documents.

- **Microsoft-documented**: stated on Microsoft Learn, a Microsoft pricing page or a Microsoft licensing document.
- **User-reported**: stated by a user or volunteer on Microsoft Q&A (learn.microsoft.com/answers), Microsoft's own question-and-answer forum. Answers there come from users, volunteer moderators and sometimes artificial intelligence (AI) generated replies, so they show that a problem occurs, not how often.
- **Page date** is the `ms.date` value Microsoft Learn publishes in each page's metadata (shown on the page as "Last updated" or similar). For forum threads it is the post timestamp.

**Access limits that shape this note.** The Fabric Ideas forum (where Power BI ideas and their vote counts now live), the Microsoft Fabric Community forums, the Power BI blog (powerbi.microsoft.com/blog) and the review sites Gartner Peer Insights, G2 and TrustRadius all returned HTTP 403 (blocked) on 16 October 2026. I did not try to get around those blocks. As a result, **no Ideas vote counts appear in this note**, and the user-reported evidence comes only from Microsoft Q&A. Treat the "how widespread" notes as weak.

## What the knowledge wiki already holds

I read `wiki/index.md` and searched `wiki/` for "Power BI" (read only, nothing edited). The wiki holds no research on Power BI problems. It mentions Power BI only in passing:

- `wiki/entities/grafana.md` (updated 2026-10-13, confidence medium): "most finance teams know Power BI, not Grafana. Power BI Pro costs AU$21 per user a month (Microsoft Australian pricing, as reported 1 October 2026)."
- `wiki/topics/council-platform-competitors.md` (updated 2026-10-13, confidence medium): Power BI consultant dashboards listed as a competitor with "Bespoke builds, per-user licences, no standard metric set".
- `wiki/sources/2026-research-findings-r15-market-and-partners.md` (updated 2026-10-04, confidence medium): "No evidence on whether buyers prefer Power BI, Grafana or a static report."
- `wiki/projects/climate-scenario-packs.md` (updated 2026-10-10) and `wiki/topics/partner-channels.md` (updated 2026-10-04): dashboard format (Power BI, Grafana or static report) is an open question for outreach.
- `raw/inbox/2026-10-14-jasila-public-dashboards.md`: some New South Wales councils publish Power BI dashboards (Northern Beaches, Blue Mountains, the NSW Net Zero Emissions Dashboard).

Everything below is new research.

---

## 1. The application itself

### 1.1 Power BI Desktop runs only on Windows

**Problem.** The main authoring tool, Power BI Desktop, has no macOS or Linux version.

**Why it matters.** Mac-based analysts and consultants need a Windows machine, a virtual machine or a cloud desktop to build models, which adds cost and support work.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/powerbi-implementation-planning-user-tools-devices (page date 30 December 2024): "Power BI Desktop is available as a Windows desktop application."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop (page date 9 October 2026), minimum requirements: "Windows 10 or Windows Server 2016 or later. For Windows on ARM, the 2025-09 Cumulative Update is required". Same page: "Running Power BI Desktop as a virtualized application (for example, as a published Citrix application) isn't supported."
- User-reported. https://learn.microsoft.com/en-ca/answers/questions/5552084/power-bi-desktop-possible-for-mac-book-pro (question and answers 11 September 2025). A forum adviser (not identified as Microsoft staff) answered: "Power BI Desktop is not natively supported on macOS and remains Windows-only as of September 2025." A user replied: "how coult it be possible ? this is incredible !" (spelling as posted).
- User-reported. https://learn.microsoft.com/en-us/answers/questions/1862712/power-bi-desktop-on-macbook-pro (12 August 2024), same question from a student.

**How widespread.** One search of Microsoft Q&A returned eight separate threads asking for Power BI Desktop on a Mac (2022 to 2025); I opened two. Each opened thread showed "Same question (0)". The Fabric Ideas vote count for a Mac version: not opened (site blocked).

**Mitigation (documented).**
- Same user-tools page: "For content creators that use a non-Windows operating system (such as macOS, Linux, or Unix), web-based authoring in the Power BI service is a viable option."
- Download page: "Power BI Desktop is fully supported on Azure Virtual Desktop (formerly Windows Virtual Desktop) and Windows 365."
- https://learn.microsoft.com/en-us/power-bi/transform-model/service-edit-data-models (page date 14 August 2026) documents editing semantic models in the browser, with limits: "These capabilities aren't supported for Direct Lake tables."

### 1.2 Memory and performance on ordinary laptops

**Problem.** Desktop imports and processes data on the author's own machine, so large data loads can take over a laptop's resources.

**Why it matters.** Staff on standard-issue laptops hit slow refreshes and an unresponsive machine; organisations end up buying higher-specification hardware for report authors.

**Sources.**
- Microsoft-documented. Download page (9 October 2026): "Memory (RAM): At least 2 GB available, 4 GB or more recommended." and "Display: At least 1440x900 or 1600x900 (16:9) required." Also: "If you set your display to change the size of text, apps, and other items to more than 100%, you won't see some dialogs that you must interact with to continue using Power BI Desktop."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-evaluation-configuration (page date 1 November 2025) lists the scenario "Power BI is taking too much of the machine's resources when importing data or executing DirectQuery queries."

**Mitigation (documented).**
- Same evaluation page, for that scenario: "Decrease maximum number of simultaneous evaluations, available memory per evaluation and/or maximum number of concurrent jobs."
- https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction (page date 30 December 2024): "Perhaps the most effective technique to reduce a model size is to load pre-summarized data." The same page lists "Remove unnecessary columns" as a technique.

The 2 GB minimum is Microsoft's floor for the program, not a sizing figure for real models. A source giving recommended laptop memory for a given model size: Not found in an opened source.

### 1.3 Monthly updates, only the latest version supported, and changes that break things

**Problem.** Desktop changes every month, only the newest build is supported, and some monthly changes switch off older behaviour.

**Why it matters.** Information technology (IT) teams that hold software back for testing fall out of support, while teams that update automatically can see reports or workflows change without warning.

**Sources.**
- Microsoft-documented. Download page (9 October 2026): "Microsoft updates and releases Power BI Desktop monthly, incorporating customer feedback and new features. Only the latest version of Power BI Desktop is supported. If you contact Support for Power BI Desktop, you're asked to upgrade the application to the latest version."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-latest-update (August 2026 update page, page date 18 August 2026): "Starting in October, users with Power BI Desktop versions from March 2026 or earlier will no longer be able to save and share files to OneDrive and SharePoint."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-latest-update-archive (page date 18 August 2026), July 2026 update: "When downloading a .pbix file from a semantic model, users now get an empty report with the dataset only. To download the report with the dataset, go to the report in the Power BI Service."
- Same archive: "Existing semantic models created using the legacy experience stop refreshing on July 31, 2026, and stop loading on August 31, 2026." (legacy Import Excel and CSV experience in the Power BI service).
- User-reported. https://learn.microsoft.com/en-gb/answers/questions/5791325/how-can-i-get-an-older-version-of-power-bi-as-the (27 February 2026): "Since feb power bi release, none of my dashboards work with the same irreporable error" (spelling as posted). "Same question (0)".

**Mitigation (documented).**
- Download page: the Microsoft Store version gives "Automatic updates" and "IT roll-out enabled". For organisations that want to control timing, the same page documents a `DisableUpdateNotification` registry value and says: "Some organizations might not want users to update to each new version."
- The archive page links to the "Power BI Desktop monthly update archive" for older builds; the download page warns that "Newer releases can't be opened by previous versions".

### 1.4 Version mismatch between Desktop, the service and Report Server

**Problem.** Files saved in a newer Desktop cannot be opened in an older one, and on-premises Power BI Report Server needs its own separate Desktop build.

**Why it matters.** Mixed versions across a team cause files that will not open; organisations using Report Server must manage two Desktop installs.

**Sources.**
- Microsoft-documented. Download page (9 October 2026): "Newer releases can't be opened by previous versions, so match the version your team uses." and "The Microsoft Store and executable versions both install the latest version, which stays current with the Power BI service. For the closest match to service features, use the latest version."
- Microsoft-documented. Same page, known issues: "Some users might encounter an error message similar to the following message when they use an outdated version of Power BI Desktop: *We weren't able to restore the saved database to the model*."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/report-server/install-powerbi-desktop (page date 1 November 2025): "This release is different from the Power BI Desktop used with the Power BI service. Using this release makes sure that the report server can interact with a known version of the reports and model."

**Mitigation (documented).** Download page: "Updating to the current version of Power BI Desktop usually resolves this issue." The Report Server build "can be installed side by side" with the standard one.

### 1.5 Crashes, failure to start and damaged files

**Problem.** Desktop can fail to start because of its embedded browser component (WebView2), unsupported environments or emulation on ARM laptops.

**Why it matters.** Desktop depends on a separate runtime component (WebView2), and on Windows on ARM it needs a specific Windows update, so device and image choices affect whether it starts.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-error-launching-desktop (page date 9 October 2026): "If WebView2 isn't installed, an earlier version is installed, or the installation is damaged, Power BI Desktop doesn't start and displays a gray window or an error message that mentions WebView2."
- Microsoft-documented. Download page: "Power BI Desktop doesn't support running with a system account because WebView2 doesn't support system accounts."
- User-reported. https://learn.microsoft.com/en-us/answers/questions/5952506/power-bi-desktop-crashes-on-startup-on-surface-pro (20 July 2026): on a Surface Pro 11 with a Snapdragon (ARM64) processor, "Power BI Desktop does not start at all. No splash screen or user interface is displayed. The process immediately crashes." "Same question (0)".

**File corruption.** A Microsoft-documented statement on PBIX file corruption rates or causes: Not found in an opened source.

**Mitigation (documented).** Startup page: "Update or reinstall WebView2 by using the following steps, which don't require elevated administrative permissions."

---

## 2. Data and refresh

### 2.1 Scheduled refresh limits by licence

**Problem.** Without Premium or Fabric capacity a model can refresh on schedule only eight times a day, and each refresh must finish within two hours.

**Why it matters.** Near-real-time reporting and large overnight loads often do not fit on Pro alone, which pushes organisations toward capacity.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data (page date 18 September 2026):
- "Power BI limits semantic models on shared capacity to eight scheduled daily semantic model refreshes."
- "If the semantic model resides on a Premium capacity, PPU, or Fabric capacity, you can schedule up to 48 refreshes per day in the semantic model settings."
- "the shared-capacity limitation for daily refreshes applies to both scheduled refreshes and refreshes triggered through the REST API." "Manual UI-triggered on-demand refreshes aren't included in the eight scheduled refresh limitation."
- "Data refreshes must complete in less than two hours on shared capacity." "On Premium, the maximum refresh duration is five hours, but using XMLA endpoint to refresh data can bypass the five-hour limit."

(PPU means Premium Per User; XMLA means XML for Analysis, the endpoint external tools use.)

**Mitigation (documented).** Same page: models on capacity "with the XMLA endpoint enabled for read-write support effectively unlimited refresh operations when configured programmatically with TMSL or PowerShell (subject to capacity resources and concurrency limits)". Also: "consider using incremental refresh for semantic models that are larger than 1 GB or that take several hours to refresh."

### 2.2 Refresh switches itself off

**Problem.** The service turns off a refresh schedule after repeated failures or when nobody has opened the reports for two months.

**Why it matters.** Reports quietly go stale, and the only signal is an email to the model owner, who may have left.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh (page date 13 February 2026): "Power BI deactivates your refresh schedule after four consecutive failures or when the service detects an unrecoverable error that requires a configuration update, such as invalid or expired credentials. It is not possible to change the consecutive failures threshold." And: "After two months of inactivity, scheduled refresh on your semantic model is paused."

**Mitigation (documented).** refresh-data page: "Microsoft recommends that you leave the checkbox **Send refresh failure notification emails semantic model owner** enabled."

### 2.3 Semantic model size limits

**Problem.** A model in a Pro workspace is capped at 1 GB; larger models need PPU or capacity, and each capacity size has its own memory ceiling.

**Why it matters.** Growth in data volume can force a licence change or a model redesign.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/enterprise/service-premium-large-models (page date 17 June 2025): "The default size limit is 1 GB." "For Pro workspaces assigned to the Reserved Capacity for Pro Workspaces, the semantic model size limit is 1 GB." "Large semantic models in the service don't affect the Power BI Desktop model upload size, which is still limited to 10 GB."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction (30 December 2024): "Shared capacity can host models up to 1 GB in size, while Premium capacities can host larger models depending on the SKU."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/enterprise/service-premium-per-user-faq (page date 27 May 2025): PPU model size limit "100 GB" and "For datasets, the 100-GB limit is documented in the Capacities and SKUs table."
- Microsoft-documented. https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-premium-what-is (page date 15 June 2026), "Max memory (GB)" column: F2 3, F4 3, F8 3, F16 5, F32 10, F64 25, F128 50, F256 100, F512 200, F1024 and above 400. Footnote: "The Max memory (GB) column represents an upper bound for the semantic model size. However, an amount of memory must be reserved for operations such as refreshes and queries on the semantic model."

(SKU means stock-keeping unit, Microsoft's term for a purchasable size.)

**Mitigation (documented).** Large-models page: semantic models "can exceed the default size limit if the Large semantic model storage format setting is enabled." Data-reduction page as in 1.2.

### 2.4 On-premises data gateway upkeep and failures

**Problem.** Reaching data inside the network needs a gateway server that must be updated monthly, and only recent versions are supported.

**Why it matters.** The gateway is a server someone must install, update and monitor; refreshes that depend on it fail when it has problems.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-onprem (page date 10 June 2025): "Currently, Microsoft actively supports only the last six releases of the on-premises data gateway. We release a new update for data gateways every month." Also: "There's a limitation of 1,000 data sources maximum on each enterprise or personal gateway cluster."
- Microsoft-documented. https://learn.microsoft.com/en-us/data-integration/gateway/service-gateway-tshoot (page date 11 June 2025): "You might encounter installation failures if the antivirus software on the installation machine is out of date."
- User-reported. https://learn.microsoft.com/en-us/answers/questions/5968159/no-able-to-do-perform-scheduled-refresh-in-power-b (6 August 2026): "Semantic Model Refresh is not happening as the Data Credentials is greyed out". "Same question (1)". The volunteer moderator's only advice was to post on the Fabric Community forum.

**Mitigation (documented).** Troubleshooting page: "If you're experiencing issues with the version you're using, try upgrading to the latest one as your issue might be resolved in the latest version."

### 2.5 DirectQuery limits and speed

**Problem.** DirectQuery (querying the source live instead of importing) caps intermediate results at one million rows and is only as fast as the source system.

**Why it matters.** Teams choose DirectQuery to avoid refresh limits and then find slow visuals, load on operational databases and modelling restrictions.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-directquery-about (page date 25 September 2025):
- "Any query (or intermediate operation) that returns more than 1,000,000 rows fails. Premium capacities can raise this limit".
- "Interactive performance depends on source latency and concurrency. Aim for common visual refresh times under 5 seconds; more than 30 seconds degrades usability."
- "Power Query folding is required for scalable performance."

Export from DirectQuery models is also capped: https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-export-data (page date 18 August 2026): "When you're using DirectQuery, the maximum amount of data that Power BI can export is 16-MB uncompressed data."

**Mitigation (documented).** DirectQuery page: "Use import by default. ... Move beyond import only when specific constraints (latency, size, governance, security, or architecture) require it." It also names hybrid tables, Direct Lake and live connections as alternatives.

### 2.6 Incremental refresh has strict requirements

**Problem.** Incremental refresh (refreshing only recent data) needs date/time parameters with exact names and, in practice, a source that can filter by date.

**Why it matters.** Done wrong, it silently loads the whole table every time; done right, it also stops you downloading the model back to Desktop.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/incremental-refresh-overview (page date 24 September 2025): "Table data is filtered by using Power Query date/time parameters with the reserved, case-sensitive names RangeStart and RangeEnd." And: "the query mashup engine might compensate and apply the filter locally, which requires retrieving all rows for the table from the data source. This can cause incremental refresh to be slow, and the process can run out of resources either in the Power BI service or in an on-premises data gateway - effectively defeating the purpose of incremental refresh." Also: "the real-time DirectQuery partition is only supported for models in Premium capacities."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/create-reports/service-export-to-pbix (page date 26 March 2026): "This option isn't available because the data model has incremental refresh enabled."

**Good news (documented).** Same overview page: "Incremental refresh is supported for Power BI Premium, Premium per user, Power BI Pro, and Power BI Embedded models."

### 2.7 Data quality and "multiple versions of the truth"

**Problem.** Self-service lets each team build its own model, so the same measure is calculated differently in different reports.

**Why it matters.** Leaders get conflicting numbers and stop trusting the reports.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/fabric-adoption-roadmap-governance (page date 30 December 2024) lists common challenges including "Sprawl of data and reports", "Lack of trust in the data, especially for content produced by self-service content creators" and "Inconsistent reports produced without sufficient data validation".
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/fabric-adoption-roadmap-content-ownership-and-management (30 December 2024): "When many semantic models exist only support one report, it indicates opportunities to improve data reusability, improve trustworthiness, reduce maintenance, and reduce the number of duplicate semantic models." (grammar as published)

**Mitigation (documented).**
- https://learn.microsoft.com/en-us/power-bi/guidance/powerbi-implementation-planning-usage-scenario-managed-self-service-bi (30 December 2024): "This scenario is about shared semantic models that help achieve a single version of the truth."
- https://learn.microsoft.com/en-us/fabric/governance/endorsement-overview (page date 11 July 2024): a Certified badge means "an organization-authorized reviewer has certified that the item meets the organization's quality standards". The master data label is "often used to indicate that a data item is to be regarded as the authoritative, single source of truth".

---

## 3. Report interface and design

### 3.1 Visuals sample large data

**Problem.** Each visual returns a limited number of data points and samples the rest.

**Why it matters.** A chart can look complete while hiding points, which matters for outlier and audit work.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-data-points (page date 1 December 2025): "Power BI visuals can get up to 30,000 data points, but it's up to the visual authors to indicate which strategies to use. The default limit is 1,000, but the visual creator can change that up to a maximum of 30,000." Strategies include "Simple Sample : Show the first, last, and N evenly distributed items in between."

**Mitigation.** A documented fix beyond choosing visuals with suitable reduction strategies: Not found in an opened source.

### 3.2 Too many visuals slow a page

**Problem.** Every visual sends its own query, so busy pages and poorly built custom visuals slow the report.

**Why it matters.** Slow reports are abandoned; on capacity they also burn compute.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/power-bi-optimization (page date 30 December 2024): "It's highly recommended you limit the number of visuals on a particular report page to only what is necessary." And: "Poorly optimized Power BI visuals can negatively affect the performance of the entire report."

**Mitigation (documented).** Same page: "Drillthrough pages and report page tooltips are great ways to provide additional details without jamming more visuals onto the page."

### 3.3 Mobile layout is a separate, manual job

**Problem.** Phone-friendly layouts must be built separately for each page, and they show only in the mobile apps, never in a phone browser.

**Why it matters.** Most reports are designed for widescreen monitors; mobile users get hard-to-read pages unless someone does extra work.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-create-mobile-optimized-report-about (page date 21 April 2026): "reports designed for use on a computer can be difficult to read and interact with on phones." "Mobile-optimized report views display only when you use the Power BI mobile apps for iOS and Android. When viewed through a web browser, reports always display in the standard, non-optimized view."

**Mitigation (documented).** Same page: "An auto-create mobile layout option in the mobile layout view that automatically generates a mobile-optimized version of your report on the layout canvas."

### 3.4 Accessibility depends on the report author

**Problem.** Power BI has accessibility features, but alt text, tab order and colour choices must be set by each author, and some features are not read by screen readers.

**Why it matters.** Accessibility depends on each author's habits, so an organisation with accessibility obligations cannot assume its reports meet them.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports (page date 31 August 2026): "Don't use report tooltips for information that screen readers need to read. Screen readers can't read report tooltip content when the tooltip appears for a data point in a visual or from the Help tooltip icon." Known limitation: "When you use screen readers with Power BI Desktop, you get the best experience if you open your screen reader before opening any files in Power BI Desktop."

**Mitigation (documented).** Same page: "Report consumers can also view the data in a visual in a tabular format by pressing Alt+Shift+F11 ... it shows a table that is screen reader friendly." The page links a "Report accessibility checklist".

### 3.5 Export row limits

**Problem.** Exporting a visual's data stops at 30,000 rows for CSV (comma-separated values) and 150,000 rows for Excel.

**Why it matters.** Users who treat Power BI as a route to Excel hit the cap and may not notice truncated files.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-export-data (page date 18 August 2026):
- "Excel .xlsx file with live connections (up to 500,000 rows max)", "Excel .xlsx file (up to 150,000 rows max)", ".csv file (up to 30,000 rows max)".
- "For export from matrix visuals using *Data with current layout*, the export limit is 150,000 *data intersections*."
- When the limit is hit: "*Exported data exceeded the allowed volume. Some data might have been omitted.*" is added at the footer of the Excel file.
- "The export to a *.csv* file doesn't contain any subtotal or total rows."

**Mitigation (documented).** Same page: "consider reducing the number of row or column categories, limiting the number of measures, or filtering the data." The live-connection Excel option raises the cap to 500,000 rows. Paginated reports export to "PDF, Excel, Word, CSV, XML, MHTML" (Report Builder page, below).

### 3.6 Paginated reports need a second tool and a different mindset

**Problem.** Interactive Power BI reports do not print well, so print-ready output needs paginated reports built in a separate Windows tool, Power BI Report Builder.

**Why it matters.** Organisations that need statutory or board-pack style output must train people on two authoring tools.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/report-paginated-or-power-bi (page date 30 December 2024): for interactive reports, "if printed, it won't be possible to scroll to reveal any out-of-view data." "Power BI paginated reports are optimized for printing, or PDF generation."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/paginated-reports/paginated-reports-report-builder-power-bi (page date 1 December 2025): "Power BI Report Builder is the standalone tool for authoring paginated reports for the Power BI service." "License requirements for Power BI paginated reports (.rdl files) are the same as for Power BI reports (.pbix files)."

**Mitigation (documented).** https://learn.microsoft.com/en-us/power-bi/paginated-reports/report-builder-power-bi (page date 1 December 2025): "Power BI Report Builder is fully supported on Azure Virtual Desktop and Windows 365."

---

## 4. Scalability and capacity

### 4.1 Fabric capacity throttling

**Problem.** When a Fabric or Premium capacity is overused, the service first delays and then rejects users' report queries.

**Why it matters.** One heavy refresh or notebook can make every report on the same capacity slow or unavailable.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/fabric/enterprise/throttling (page date 14 August 2026), throttling table:
- "Usage <= 10 minutes | Overage protection | Jobs can consume 10 minutes of future capacity use without throttling."
- "10 minutes < Usage <= 60 minutes | Interactive delay | Fabric delays user-requested interactive jobs by 20 seconds at submission."
- "60 minutes < Usage <= 24 hours | Interactive rejection | Fabric rejects user-requested interactive jobs."
- "Usage > 24 hours | Background rejection | Fabric rejects all requests."

**User-reported.** https://learn.microsoft.com/en-in/answers/questions/5879790/power-bi-reports-hitting-interactive-limit-reached (4 May 2026): after moving from F64 to an F4 trial, "Issue happens even with only 1–2 users actively interacting" and "initial page loads become extremely slow (taking more than 5 minutes; normally <1 second)". (The poster's own text contains a dash; quoted as posted.)

**Mitigation (documented).**
- Throttling page: "To see whether your capacity is overloaded, review the Utilization chart in the Microsoft Fabric Capacity Metrics app."
- https://learn.microsoft.com/en-us/fabric/enterprise/capacity-planning-troubleshoot-throttling (page date 10 July 2025): "If utilization never exceeded 100%, slowness isn't due to capacity throttling".
- Migration overview (4.5): "Scale up on demand through the Azure portal if you see sustained throttling."

### 4.2 Smoothing delays the pain and stretches it out

**Problem.** Fabric spreads the cost of background jobs over 24 hours, so overload builds quietly and throttling continues until the debt is paid off.

**Why it matters.** Capacity problems show up hours after the cause, which makes them hard to diagnose and budget for.

**Source.** Microsoft-documented. Throttling page (14 August 2026): "With smoothing, Fabric spreads the compute cost for background jobs over 24 hours." "Fabric smooths interactive operations over a minimum of five minutes, and up to 64 minutes depending on how much CU usage they consume." "Throttling enforcement continues until unused capacity pays off all carryforward CUs." (CU means capacity unit.)

**Mitigation (documented).** Same page: "By increasing your SKU, you burndown carryforward faster because each timepoint has more idle capacity."

### 4.3 Small Fabric SKUs are small

**Problem.** The cheaper F2 to F32 capacities have low memory and connection limits, and every viewer still needs a paid licence.

**Why it matters.** Organisations that pick a small SKU to save money can end up with both throttling and per-user licence costs.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/support/premium-migration-overview (page date 22 July 2026): "On F64 and larger, users with a Fabric Free license and the Viewer role can view content, the same as on P SKUs. On F2 through F32, every viewer needs a Pro or PPU license."
- Microsoft-documented. service-premium-what-is (15 June 2026), F2 row: Max memory 3 GB, max concurrent DirectQuery connections per semantic model 5, live connection per second 2, model refresh parallelism 1.

### 4.4 Concurrency ceilings per SKU

**Problem.** Each capacity size caps simultaneous DirectQuery connections, live-connection queries per second and parallel refreshes.

**Why it matters.** Month-end peaks or many simultaneous viewers can queue even when average use looks fine.

**Source.** Microsoft-documented. service-premium-what-is (15 June 2026): "Max concurrent DirectQuery connections (per semantic model)" ranges from 5 (F2) to 200 (F512 and above); "Live connection (per second)" from 2 (F2) to 960 (F2048 and above); "Model refresh parallelism" from 1 (F2) to 1,280 (F2048 and above). F64: 50 connections, 30 per second, 40 parallel refreshes. Footnote: "The Microsoft Fabric Capacity Metrics app doesn't currently expose these metrics."

### 4.5 Retirement of Premium per capacity (P SKUs)

**Problem.** Microsoft is retiring Power BI Premium P SKUs and organisations must move to Fabric F SKUs when their agreement ends.

**Why it matters.** A forced migration with a deadline, a new billing model and possible cost changes.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/support/premium-migration-overview (page date 22 July 2026): "Microsoft is retiring Power BI Premium per-capacity SKUs (P SKUs). Each P SKU subscription ends at the end of its current agreement term, and Microsoft no longer sells new P SKUs." "Starting on day 31, access is throttled (interactive operations are delayed). On day 91 and beyond, all operations are rejected - your data is retained but inaccessible until you migrate the workspaces to a Fabric F SKU capacity or delete the capacity." "If your Enterprise Agreement is still active, you can continue running existing P SKU capacity and renew it annually through your agreement until the EA term ends." "Per-user licenses aren't affected." Power BI Report Server is "Still available, with a Fabric capacity reservation or SQL Server Enterprise Edition with Software Assurance."

**Mitigation (documented).** Same page: "Track spend daily for the first 30 days by using Microsoft Cost Management." Microsoft's April 2025 licensing deck (see 6.3), slide 17: "Simply reassign workspaces to the new F-SKU capacity" and "Bulk reassign to save time".

### 4.6 Large models need much more memory than their size

**Problem.** A model needs memory headroom for refreshes and queries, so the largest model a capacity can hold is less than its stated memory.

**Why it matters.** Sizing a capacity from model size alone leads to failed refreshes.

**Source.** Microsoft-documented. service-premium-what-is (15 June 2026): "Three separate actions determine the amount of memory attributed to the original semantic model, which might be larger than two times the semantic model size." Large-models page: "A single semantic model is still constrained to the memory limits of the SKU."

---

## 5. Usability and skills

### 5.1 DAX is hard to learn well

**Problem.** DAX (Data Analysis Expressions), Power BI's formula language, depends on evaluation context, which many users find hard to reason about.

**Why it matters.** Wrong measures look plausible; organisations need people who can write and review DAX.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/dax/dax-overview (page date 20 October 2023): "Context is a powerful concept that can also make it difficult to troubleshoot formulas." Also: "nesting can make it difficult to create or troubleshoot formulas."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/fabric-adoption-roadmap-mentoring-and-user-enablement (30 December 2024): "It's common for some tough issues to come up during office hours that cannot be solved quickly, such as getting a complex DAX calculation to work".

**Mitigation (documented).** The mentoring page recommends office hours and a centralised portal. Microsoft's starter page: https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-quickstart-learn-dax-basics (page date 11 April 2025).

A survey measuring how many users struggle with DAX: Not found in an opened source.

### 5.2 Self-service sprawl

**Problem.** Without rules, users create many workspaces, duplicate models and copies of reports.

**Why it matters.** Duplication raises cost, slows refresh windows, and spreads conflicting figures.

**Source.** Microsoft-documented. Governance roadmap page (30 December 2024) lists "Duplicate effort spent across business units", "Fragmented, siloed, and duplicated data" and "Lack of data catalog, inventory, glossary, or lineage". It also warns: "If you don't make governance decisions and communicate them well, users will use their own judgment for how things should work—and that often results in inconsistent approaches to common tasks." (the em dash is Microsoft's)

**Mitigation (documented).** Same page lists decisions to make, including "Who is permitted to create a workspace", "How to manage workspaces effectively" and "Requirements for who can certify content". Endorsement as in 2.7.

### 5.3 Version control: PBIX is a binary file

**Problem.** The standard .pbix file cannot be diffed or merged in source control.

**Why it matters.** No line-by-line change history, no code review, and no safe way for two developers to merge work.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/guidance/powerbi-implementation-planning-content-lifecycle-management-develop-manage (page date 30 December 2024): "a .pbix file is a binary file, and there aren't supported methods to view or modify its contents."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview (page date 23 September 2026), Power BI Project (PBIP) limits: "Sensitivity labels aren't supported with Power BI projects." "Can I convert PBIX into PBIP and vice-versa programmatically? Answer: No."

**Mitigation (documented).** Projects overview: with PBIP, "report and semantic model item definitions are saved as individual plain text files in a simple, intuitive folder structure." Develop-and-manage page: with text formats "You can more easily merge changes without creating conflicts."

### 5.4 Collaborating on one file

**Problem.** Two people cannot co-edit one PBIX in Desktop, and republishing a shared PBIX overwrites what is in the service.

**Why it matters.** Teams lose work or block each other on a single file.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-report-lifecycle-datasets (page date 3 December 2024): "If the owner modifies the original shared .pbix file, the shared semantic model and report in the Power BI service are overwritten." "Members of a workspace can't replace the original shared report."
- A Microsoft-documented statement that Desktop has no co-authoring: Not found in an opened source. A Microsoft Q&A answer (https://learn.microsoft.com/en-us/answers/questions/5912563/manage-access-to-power-bi-report-with-edit-rights, 5 June 2026) recommends "check-in/check-out" through SharePoint or Teams versioning; I read only that fragment.

**Mitigation (documented).**
- https://learn.microsoft.com/en-us/power-bi/guidance/report-separate-from-model (30 December 2024): "It makes sense to separate model and report development into separate Power BI Desktop files when: Data modelers and report authors are different people."
- Web editing page (14 August 2026): "In this experience, users can work and collaborate simultaneously on the same semantic model."

---

## 6. Licensing and cost

### 6.1 Current per-user prices

**Problem.** Every author, and every viewer outside large capacity, needs a paid licence.

**Why it matters.** Per-user cost scales with headcount.

**Sources.**
- Microsoft-documented. https://www.microsoft.com/en-us/power-platform/products/power-bi/pricing (no date shown): Power BI Pro "$14.00 user/month, paid yearly"; Power BI Premium Per User "$24.00 user/month, paid yearly". Footnote 2: "A $14.00 per user/month,paid yearly add-on is available for users with Power BI Pro, Microsoft 365 E5, and Office 365 E5 licenses to step up to Power BI Premium per user." (US dollar pricing page. The add-on figure equals the Pro price, not the $10 gap between Pro and PPU; I quote it as published and have not resolved the difference.)
- Microsoft-documented. Microsoft "Power BI Licensing Deck", https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents//Power-BI-Licensing-Deck-April25.pdf (PDF metadata date 23 April 2025), slide 3: Pro "$14 user/month", PPU "$24 user/month"; slide 6: Pro "Included in Office 365 E5 and Microsoft 365 E5".

**Price change history.** The previous prices and the effective date of the increase: **Not found in an opened source.** Microsoft's announcement ("Important update to Microsoft Power BI pricing", https://powerbi.microsoft.com/en-us/blog/important-update-to-microsoft-power-bi-pricing/) returned HTTP 403 and was not opened. Search snippets suggested an effective date of 1 April 2025 and earlier prices of about US$10 (Pro) and US$20 (PPU); these are not evidence and need checking on the laptop.

### 6.2 PPU content cannot be shared with Pro users

**Problem.** Content in a PPU workspace can be viewed only by other PPU users.

**Why it matters.** Mixing Pro and PPU licences creates islands of content that some staff cannot open.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/fundamentals/service-features-license-type (page date 24 August 2026): "With a PPU license, you can share content only with users who also have a PPU license. The exception is when that content is saved in a workspace hosted in Premium capacity." Also: "A Premium Per User (PPU) workspace isn't the same as a Premium capacity workspace."

### 6.3 Free viewers need F64 or larger

**Problem.** Staff with free licences can view shared reports only when the workspace sits on an F64 (or P1) or larger capacity.

**Why it matters.** Organisations face a step change: licence everyone with Pro, or buy a large capacity.

**Sources.**
- Microsoft-documented. service-features-license-type (24 August 2026): "Pro and PPU users can share content and collaborate with free users if the content is saved in workspaces hosted in Premium capacity, Fabric F64, or greater capacity."
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/consumer/end-user-license (page date 25 November 2025): free licence "View shared content in non-Premium workspaces | No".
- Microsoft-documented. Licensing deck (April 2025), slide 11, US West 2 prices: F64 "$8,409.6" pay-as-you-go monthly and "$5,002.667" reservation monthly. Note 3: "Power BI Pro license is required for all Power BI Premium ("P") and Fabric Capacity ("F") SKUs to publish Power BI content to Microsoft Fabric. Enabling content consumers to review and interact with Power BI reports without additional paid per-user licenses is available at F64 and above (and P1 and above)."
- The current pricing page footnote 3 says the same: "A Power BI Pro license is required for all Power BI Premium ("P") and Fabric Capacity ("F") SKUs".

**Worked comparison (my arithmetic, Python):**

```
f64_res=5002.667; f64_payg=8409.6; pro=14.0
print('F64 reservation / Pro =', round(f64_res/pro,1))   # 357.3
print('F64 PAYG / Pro =', round(f64_payg/pro,1))          # 600.7
print('F64 PAYG check 0.18*730*64 =', round(0.18*730*64,1))  # 8409.6
```

So at April 2025 US West 2 list prices, an F64 reservation costs about the same per month as 357 Pro licences (601 on pay-as-you-go). Authors still need Pro on top. Regional prices differ; current Fabric prices were not checked (the Azure pricing page was not opened).

### 6.4 Sharing outside the organisation

**Problem.** External guests need a licence route, and several features do not work for them.

**Why it matters.** Partner, supplier and client-facing reporting is harder than internal sharing.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-admin-entra-b2b (page date 3 November 2025): "To invite guest users, you need a Power BI Pro or Premium Per User (PPU) license. Pro trial users can't invite guest users in Power BI." Licence routes: Premium capacity, "Assign a Power BI Pro or Premium Per User (PPU) license to guest user", or "Guest user brings their own Power BI Pro or Premium Per User (PPU) license". But "'Bring your own license' doesn't work across different Microsoft Azure clouds for B2B guest users." Unsupported for guests include "Direct publishing from Power BI desktop to the Power BI service", "Guest users can't use Analyze in Excel" and "Guest users can't be @mentioned in commenting". (B2B means business-to-business guest access through Microsoft Entra ID.)

---

## 7. Security and governance

### 7.1 Row-level security does not apply to editors

**Problem.** Row-level security (RLS) filters data only for people with the Viewer role; workspace Admins, Members and Contributors see everything.

**Why it matters.** Giving a business user "Member" so they can edit silently removes their data restrictions.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/fabric/security/service-admin-row-level-security (page date 13 May 2026): "RLS only restricts data access for users with Viewer permissions. It doesn't apply to workspace Admin, Member, or Contributor roles." Further limits: "Service principals can't be added to an RLS role. Accordingly, RLS isn't applied for apps using a service principal as the final effective identity." "With RLS enabled, using the USERELATIONSHIP() function in DAX queries and measures might cause unexpected errors." "The Test as role/View as role feature doesn't work for paginated reports." For B2B guests, USERPRINCIPALNAME() "can appear as either: The external user's email address (user@partner.com), or A tenant-resolved value such as user_partner.com#EXT#@tenant.onmicrosoft.com".

**Mitigation (documented).** Same page: "Use the View as role feature ... to validate that your filter returns the expected rows before publishing the report."

### 7.2 Tenant settings are not a security boundary

**Problem.** Turning off a feature such as Export in the admin portal does not remove the user's underlying data permission.

**Why it matters.** Organisations that rely on admin switches for data protection have a false sense of security.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/fabric/admin/about-tenant-settings (page date 1 September 2026): "Tenant settings that control the availability of features in the Power BI user interface can help to establish governance policies, but they're not a security measure. For example, the Export data setting doesn't restrict the permissions of a Power BI user on a semantic model. Power BI users with read access to a semantic model have the permission to query this semantic model and might be able to persist the results without using the Export data feature". Also: "It can take up to 15 minutes for a setting change to take effect for everyone in your organization."

**Mitigation (documented).** Restrict semantic model permissions (Build, Read) and use labels and monitoring (7.4).

### 7.3 Publish to web makes reports public

**Problem.** Publish to web creates a public link that anyone on the internet can open without signing in.

**Why it matters.** A single user can expose confidential data.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-web (page date 1 November 2025): "When you use Publish to web, anyone on the Internet can view your published report or visual. Viewing requires no authentication. Don't publish confidential or proprietary information."

**Mitigation (documented).** https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-sharing (page date 8 April 2026): "Admins can set Publish to web to Enabled and Choose how embed codes work to Allow only existing embed codes." The setting can also be limited to "Specific security groups".

### 7.4 Export and sensitivity labels

**Problem.** Sensitivity labels follow data into Excel, PowerPoint and PDF exports, but not into CSV, and they need extra licences.

**Why it matters.** Labelled data can still leave unprotected, and the labelling programme carries a separate licence cost.

**Sources.**
- Microsoft-documented. Export page (18 August 2026): "The first two support sensitivity labels. The third option, exporting to .csv, doesn't support sensitivity labels."
- Microsoft-documented. https://learn.microsoft.com/en-us/fabric/governance/information-protection (page date 13 July 2026): "Requirements An appropriate license for Microsoft Purview Information Protection." "To be able to apply labels to Power BI items, a user must have a Power BI Pro or Power BI Premium Per-User (PPU) license in addition to the licenses needed for Microsoft Purview Information Protection."
- PBIP files do not support labels (5.3).

**Mitigation (documented).** Export page: "organizations can use Microsoft Defender for Cloud Apps to configure a policy that prevents users from downloading sensitive data from Power BI to unmanaged devices." Report designers can choose to "Don't allow end users to export any data".

### 7.5 Copilot needs capacity and admin switches, and consumes capacity

**Problem.** Copilot in Power BI does not work on Pro or PPU alone; it needs a paid Fabric (F2 or larger) or Premium (P1 or larger) capacity, tenant settings, and a supported region, and it uses capacity units.

**Why it matters.** "Turning on Copilot" is a capacity purchase and a data-residency decision, not a licence tick-box.

**Sources.**
- Microsoft-documented. https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-introduction (page date 24 August 2026): "Paid Fabric capacity (F2 or higher) or Power BI Premium (P1 or higher)." "A Power BI Pro or Premium Per User (PPU) license alone isn't sufficient—Copilot requires organizational capacity." (em dash is Microsoft's) "If your tenant or capacity is outside the United States or EU data boundary, Copilot is disabled by default unless your Fabric tenant admin enables the tenant setting called Data sent to Azure OpenAI can be processed outside your tenant's geographic region, compliance boundary, or national cloud instance". "The standalone Copilot and Copilot in apps experiences aren't yet available in the following regions", a list that includes "Germany North" and "Norway West".
- Microsoft-documented. https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-fabric-consumption (page date 22 May 2026): "Requests to Copilot in Fabric consume Fabric capacity units (CUs)." Rates per 1,000 tokens: input "100 CU seconds", cached input "10 CU seconds", output "400 CU seconds". "Copilot operations in Fabric are classified as background jobs".

**Relevance to Helsinki.** Finland is inside the EU data boundary, so the cross-geography default-off rule applies only if the capacity sits outside it. Whether Finland Central or other Nordic regions support standalone Copilot: the excluded list names Norway West and Germany North; Finland is not named. A positive statement that Finland is supported: Not found in an opened source.

---

## 8. Other issues organisations raise

### 8.1 Retirements and deprecations announced for 2025 to 2027

**Problem.** Several features are being withdrawn, and replacements often move work into Fabric or Copilot.

**Why it matters.** Reports built on retiring features need rework on Microsoft's timetable.

**Sources (all Microsoft-documented).**
- Q&A (natural language questions): https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-limitations and https://learn.microsoft.com/en-us/power-bi/natural-language/q-and-a-intro (both page date 22 May 2026): "Q&A experiences are going away in February 2027."
- Streaming: https://learn.microsoft.com/en-us/power-bi/connect-data/service-real-time-streaming (page date 27 January 2025): "Creation of streaming models remains enabled until October 31, 2027." "Microsoft recommends users explore Real-Time Intelligence in Microsoft Fabric."
- Default semantic models: https://learn.microsoft.com/en-us/fabric/data-warehouse/semantic-models (page date 5 December 2025): "By November 30, 2025, all Power BI default semantic models are disconnected from their item and become independent semantic models." "Since September 5, 2025, Power BI default semantic models are no longer created automatically when a warehouse, lakehouse, or mirrored item is created."
- Update archive (18 August 2026): "Starting April 15, 2026, the Hierarchies feature in Power BI Scorecards will be removed." "The QuickBooks Online connector is retiring and won't be supported after March 2026." Legacy Excel and CSV import (see 1.3). Old OneDrive and SharePoint file picker in Desktop (see 1.3).

Not found in an opened source: a retirement notice for Power BI dashboards themselves, and the datamart retirement (Learn datamart pages now redirect to a general hub; search snippets mentioned 1 November 2025 but I could not open a page stating it).

### 8.2 Dependence on the Microsoft stack ("lock-in")

**Problem.** Core Power BI capabilities assume other Microsoft products: Windows for authoring, Fabric capacity for Copilot and free viewers, Purview for labels, Entra ID for identity, and Fabric or SQL Server licensing for Report Server.

**Why it matters.** Moving away later means rebuilding models, DAX and security, and pricing changes in one product ripple through.

**Sources (Microsoft-documented facts, not a lock-in claim).** Desktop Windows-only (1.1); Copilot capacity requirement (7.5); labels need Purview licences (7.4); Report Server "Still available, with a Fabric capacity reservation or SQL Server Enterprise Edition with Software Assurance" (4.5); Pro needed to publish even on capacity (6.3).

An independent analyst or survey source describing Power BI vendor lock-in as a reported concern: **Not found in an opened source** (Gartner, G2, TrustRadius and Gartner Peer Insights were blocked).

### 8.3 Finding known issues is harder than it was

**Problem.** Microsoft moved its known-issues list off Microsoft Learn to a script-driven support site.

**Why it matters.** Admins and consultants must check a separate site to see whether a fault is a known product bug.

**Source.** Microsoft-documented. https://learn.microsoft.com/en-us/fabric/known-issues/fabric-known-issues (page date 21 July 2025): "Microsoft Fabric Known issues are no longer published on Microsoft Learn. To view the latest updates, visit the Fabric support page." The new page (https://support.fabric.microsoft.com/known-issues/) loaded but its issue list is drawn by script, so I could not read any entries.

---

## Conflicts between sources

1. **Copilot capacity minimum.** Licensing deck (April 2025, slide 13): "Copilot in Fabric is limited to customers who have purchased Fabric capacity (F64 or higher) or Power BI Premium capacity (P1 and above)". Copilot introduction page (24 August 2026): "Paid Fabric capacity (F2 or higher)". I trust the Learn page: it is 16 months newer and is the product documentation.
2. **Copilot consumption rates.** Deck (April 2025, slide 13): "400 Capacity Units seconds per 1,000 input tokens and 1,200 Capacity Units seconds per 1,000 output tokens". Learn consumption page (22 May 2026): input 100, output 400 CU seconds per 1,000 tokens. Trust Learn (newer).
3. **Q&A retirement date.** Search snippets of the Power BI blog said December 2026; both Learn Q&A pages (22 May 2026) say February 2027. The blog was not opened (403). Trust Learn.
4. **PPU step-up add-on price.** Pricing page footnote gives "$14.00" while the gap between Pro ($14.00) and PPU ($24.00) is $10. Unresolved; check with Microsoft or a licensing partner.

## Everything not found in an opened source

- Vote counts on any Fabric Ideas post (site blocked).
- Previous Pro and PPU prices and the effective date of the change (blog blocked).
- Microsoft-documented PBIX corruption causes or rates.
- Recommended laptop memory for a given model size.
- A Microsoft statement that Desktop has no co-authoring.
- A survey measuring the DAX learning curve.
- Power BI dashboards retirement notice; datamart retirement date.
- An analyst or survey source on vendor lock-in.
- Confirmation that standalone Copilot is available in Finland Central.
- Current (2026) Fabric capacity prices; the deck gives April 2025 US West 2 prices only.

## Pages not opened (blocked or unreadable)

- https://community.fabric.microsoft.com/t5/fabric-ideas/idb-p/fbc_ideas/ (Fabric Ideas): HTTP 403.
- https://community.fabric.microsoft.com/t5/Power-BI-forums/ct-p/powerbi: HTTP 403.
- https://powerbi.microsoft.com/en-us/blog/important-update-to-microsoft-power-bi-pricing/ and the en-in copy: HTTP 403.
- https://community.fabric.microsoft.com/t5/Power-BI-Updates-Blog/Important-update-to-Microsoft-Power-BI-pricing/ba-p/5174341: HTTP 403.
- https://www.gartner.com/reviews/market/analytics-business-intelligence-platforms/vendor/microsoft/product/microsoft-power-bi: HTTP 403.
- https://www.g2.com/products/microsoft-power-bi/reviews: HTTP 403.
- https://www.trustradius.com/products/microsoft-power-bi/reviews: HTTP 403.
- https://techcommunity.microsoft.com/blog/publicsectorblog/licensing-and-pricing-updates-for-teams-phone-and-power-bi-coming-july-1-2025/4397143: page loads but text is drawn by script; no content read.
- https://support.fabric.microsoft.com/known-issues/: same, list drawn by script.

## PDFs to fetch (for A-ron on the laptop)

- Microsoft, "Power BI Licensing Deck" (April 2025): https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents//Power-BI-Licensing-Deck-April25.pdf. Suggested name `2025-microsoft-power-bi-licensing-deck.pdf`. I read it through the fetch tool's temporary copy; it was not saved to `raw/pdfs/` because this task allowed writing only this note.

## Notes on method

- All pages opened on 16 October 2026 with a direct request and read as text. No logins, captchas, caches or archives were used.
- No page contained instructions aimed at an AI agent.
- Arithmetic in 6.3 done in Python; code and output shown there.
- Per the research rules, an inbox note in `raw/inbox/` would normally follow; this task allowed writing only this file, so none was written. A fresh fact check (separate agent, given only claims and addresses, 16 October 2026) reopened 21 key quotes from sections 1 to 8 plus the arithmetic in 6.3: all 22 marked correct, with every Learn page date matching. That checker also reported that the Copilot introduction page says trial capacities and free SKUs aren't supported; I have not reread that sentence myself.
