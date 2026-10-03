# Security policy

## Supported version

Security fixes target the latest release on the default branch.

## Reporting

Please report a suspected vulnerability privately through GitHub's security-advisory feature when the repository is published. Never include confidential pricing data in a public issue.

## Data-handling notes

Run locally, Tag Signal has no built-in size limit on CSV, XLSX, and JSON tables (Streamlit's upload cap is `TAGSIGNAL_MAX_UPLOAD_MB`, or `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` in Docker, default 10,000 MB). Any shared or public deployment should set `SIGNAL_PUBLIC=1`, which applies upload, row and column caps, and lower the upload cap. It does not execute workbook macros. Exported strings that could be interpreted as spreadsheet formulas are neutralized. Aggregate evidence exports omit row-level pricing records.

These controls do not turn Tag Signal into a hardened multi-tenant service. A hosted deployment should add authentication, TLS, authorization, rate limiting, secure headers, isolated storage, dependency monitoring, logging appropriate to the data classification, and a documented deletion policy.
