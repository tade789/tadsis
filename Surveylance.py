import streamlit as st
import pandas as pd
from datetime import datetime

# --- Insider Lists ---
directors_accounts = {"ET87CBECETA00002", "ET87CBECETA00003", "ET87CBECETA00000"}
shareholders_accounts = {"ET10CBECETA01001", "ET10CBECETA01002"}
board_accounts = {"ET10CBECETA01000", "ET10CBECETA01003"}

# --- Page Config ---
st.set_page_config(page_title="Insider Trading Watch", layout="wide")
st.title("📊 ESX - Insider Trading Watchlist Report")

st.markdown("""
Upload your trading file (`.xlsx` or `.csv`) to automatically analyze and flag:
- Insider Trading (Directors, ≥5% Shareholders, Board)
- Publication-sensitive activities
- Frequent Trading Patterns
""")

# --- Upload File ---
uploaded_file = st.file_uploader("📁 Upload Executed Orders File", type=["xlsx", "csv"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.success("✅ File uploaded successfully!")

        # Clean and preprocess
        df.columns = df.columns.str.strip()
        required_cols = {"Client", "Price", "Quantity", "Side", "Date Time", "Security"}

        if not required_cols.issubset(df.columns):
            st.error(f"❌ Missing required columns: {required_cols - set(df.columns)}")
        else:
            df['Date Time'] = pd.to_datetime(df['Date Time'])
            df['Date'] = df['Date Time'].dt.date

            # --- Sidebar Filters ---
            st.sidebar.header("🔍 Filters")
            min_date, max_date = df['Date'].min(), df['Date'].max()

            from_date = st.sidebar.date_input("📅 From Date", min_value=min_date, max_value=max_date, value=min_date)
            to_date = st.sidebar.date_input("📅 To Date", min_value=min_date, max_value=max_date, value=max_date)

            # Tabs for filters
            filter_tab, pub_tab = st.sidebar.tabs(["Security Filter", "Issuer Publications"])
            with filter_tab:
                all_securities = ["All"] + sorted(df['Security'].unique().tolist())
                selected_securities = st.multiselect("Select Securities:", options=all_securities, default="All")
                if "All" in selected_securities or not selected_securities:
                    selected_securities = all_securities[1:]

            with pub_tab:
                publication_types = {}
                st.info("Set news type for each security:")
                for sec in df['Security'].unique():
                    pub_type = st.radio(f"{sec}", ["None", "Good", "Bad"], key=f"pub_{sec}")
                    if pub_type != "None":
                        publication_types[sec] = pub_type

            # Apply filters
            mask = (df['Date'] >= from_date) & (df['Date'] <= to_date)
            df = df[mask]
            df = df[df['Security'].isin(selected_securities)]

            # --- Insider Classification ---
            df['Watch Type'] = df['Client'].apply(lambda x:
                "Director" if x in directors_accounts else
                "≥5% Shareholder" if x in shareholders_accounts else
                "Board Member" if x in board_accounts else None
            )
            insider_df = df[df['Watch Type'].notna()].copy()

            # --- Insider Reports ---
            st.subheader(" Insider Trading Reports by Category")
            for category, title in [
                ("Director", "👨‍💼 Directors"),
                ("≥5% Shareholder", "💼 ≥5% Shareholders"),
                ("Board Member", "🏛️ Board Members")
            ]:
                with st.expander(title):
                    cat_df = insider_df[insider_df['Watch Type'] == category]
                    st.dataframe(cat_df if not cat_df.empty else pd.DataFrame(columns=df.columns), use_container_width=True)

            # --- Publication-Sensitive Insider Trades ---
            with st.expander("⚠️ Publication-Sensitive Insider Trades"):
                insider_df['Publication Flag'] = insider_df.apply(
                    lambda row: (
                        "Good News Buy Alert" if publication_types.get(row['Security']) == "Good" and row['Side'].lower() == "buy" else
                        "Bad News Sell Alert" if publication_types.get(row['Security']) == "Bad" and row['Side'].lower() == "sell"
                        else None
                    ), axis=1
                )
                flagged_pub = insider_df[insider_df['Publication Flag'].notna()]
                st.dataframe(flagged_pub if not flagged_pub.empty else pd.DataFrame(columns=df.columns), use_container_width=True)

            # --- Frequent Trading Patterns ---
            with st.expander("🔁 Frequent Trading Patterns (Same Volume, Price, Opposite Sides in 2-3 Days)"):
                df_sorted = df.sort_values(['Client', 'Date Time'])
                matched_indices = set()

                for client in df_sorted['Client'].unique():
                    client_trades = df_sorted[df_sorted['Client'] == client]
                    for i in range(len(client_trades)):
                        for j in range(i+1, len(client_trades)):
                            t1 = client_trades.iloc[i]
                            t2 = client_trades.iloc[j]
                            if abs((t2['Date Time'] - t1['Date Time']).days) <= 3:
                                if (
                                    t1['Price'] == t2['Price'] and
                                    t1['Quantity'] == t2['Quantity'] and
                                    t1['Side'].lower() != t2['Side'].lower()
                                ):
                                    matched_indices.add(t1.name)
                                    matched_indices.add(t2.name)
                            else:
                                break

                freq_trades = df_sorted.loc[list(matched_indices)].sort_values(by=['Client', 'Date Time']) if matched_indices else pd.DataFrame(columns=df.columns)
                st.dataframe(freq_trades, use_container_width=True)
            
            # --- Final Report ---
            st.subheader("📋 Consolidated Insider Report List")
            if not insider_df.empty:
                st.dataframe(insider_df, use_container_width=True)
                st.download_button("📥 Download Consolidated Report", insider_df.to_csv(index=False), "insider_report.csv", mime="text/csv")
            else:
                st.info("No insider activities in selected range.")

    except Exception as e:
        st.error(f"⚠️ Error processing the file: {str(e)}")
else:
    st.warning("👆 Please upload a file to begin.")
