# Load the REBA Pricing Insights queries in Power BI Desktop

1. Open the saved PBIX (or a copy) in Power BI Desktop.
2. Select **Transform data** → **New source** → **Blank query**. For each `.m` file, open **Advanced Editor**, replace its contents with the file contents, rename the query to the matching table name (`PropertyOverview`, `RentSourceQuality`, `SourceQuality`), See then select **Close & Apply**.
3. When prompted, choose **Database** credentials for PostgreSQL at `127.0.0.1:5432`, database `portfolio`, and enter the local database username/password. Credentials are not part of this project.
4. Create the measures in `Measures.dax` on the corresponding tables. Add the visuals described in `Report Layout.md`; the existing rent grain safeguards are included there.
5. Save as a new PBIX after the data load and visuals are in place.

These `.m` files and the layout plan are source material for an interactive Power BI report; they do not claim that the blank `REBAtest.pbix` has already been populated.
