import streamlit as st
import pandas as pd
import tempfile
import os

# Import the core MassQL engine
from massql import msql_engine

st.set_page_config(page_title="MassQL Batch MGF Tester", page_icon="🔬", layout="wide")

# --- Sidebar Branding ---
with st.sidebar:
    # This looks for an image file named 'logo.png' in the same folder as app.py
    try:
        st.image("logo.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("Upload a 'logo.png' file to display the AquOmixLab logo.")
    
    # Clickable centered link
    st.markdown("<h3 style='text-align: center;'><a href='http://www.aquomixlab.com' target='_blank'>www.aquomixlab.com</a></h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.write("**About**")
    st.write("This tool performs sequential MassQL logic queries directly against .mgf MS2 data, bypassing external server dependencies.")
# ------------------------

st.title("🔬 MassQL Batch MGF Tester")
st.write("Build a list of MassQL queries and run them sequentially against an uploaded .mgf file.")

# --- 1. Initialize Session State ---
# This allows the app to remember the queries you add one by one
if 'query_list' not in st.session_state:
    st.session_state.query_list = []

# --- 2. File Uploader ---
st.markdown("### 1. Upload Data")
uploaded_file = st.file_uploader("Upload your .mgf file", type=["mgf"])

st.markdown("---")

# --- 3. Query Input Section ---
st.markdown("### 2. Add MassQL Queries")

# Create columns for layout
col1, col2 = st.columns([1, 3])
with col1:
    query_name = st.text_input("Query Name", placeholder="e.g., Query S1")
with col2:
    query_text = st.text_area("MassQL Query String", height=100, placeholder="QUERY scaninfo(MS2DATA) WHERE...")

# Buttons to add or clear queries
btn_col1, btn_col2 = st.columns([1, 6])
with btn_col1:
    if st.button("Add Query"):
        if query_name.strip() and query_text.strip():
            st.session_state.query_list.append({
                "Name": query_name.strip(), 
                "Query": query_text.strip()
            })
            st.rerun() # Refreshes the app to show the new query in the table
        else:
            st.warning("Please provide both a name and a query string.")
with btn_col2:
    if st.button("Clear All Queries"):
        st.session_state.query_list = []
        st.rerun()

# --- 4. Display Applied Queries Table ---
st.markdown("#### Applied Queries Table")
if st.session_state.query_list:
    queries_df = pd.DataFrame(st.session_state.query_list)
    st.dataframe(queries_df, use_container_width=True)
else:
    st.info("No queries added yet.")

st.markdown("---")

# --- 5. Execution Section ---
st.markdown("### 3. Run Analysis")
if st.button("Run Analysis", type="primary"):
    if uploaded_file is None:
        st.error("Please upload an .mgf file first.")
    elif not st.session_state.query_list:
        st.error("Please add at least one query to the list.")
    else:
        with st.spinner("Running MassQL engine..."):
            try:
                # Save the uploaded file to a temporary path
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mgf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                all_results = []
                
                # Run each query from the session state list sequentially
                for q_dict in st.session_state.query_list:
                    q_name = q_dict["Name"]
                    q_str = q_dict["Query"]
                    try:
                        df = msql_engine.process_query(q_str, tmp_path)
                        
                        # If matches were found, tag them with the custom name
                        if not df.empty:
                            df['Matched_Queries'] = q_name
                            all_results.append(df)
                    except Exception as e:
                        st.error(f"Syntax error in {q_name}: {e}")
                
                # Clean up the temporary file
                os.remove(tmp_path)
                
                # Process the combined results
                if not all_results:
                    st.info("All queries executed successfully, but no matching scans were found.")
                else:
                    # Combine all successful dataframes into one
                    combined_df = pd.concat(all_results, ignore_index=True)
                    
                    # Group by scan to avoid duplicates
                    meta_cols = [col for col in combined_df.columns if col not in ['scan', 'Matched_Queries']]
                    
                    # Merge the query names with a comma for scans hitting multiple queries
                    agg_dict = {'Matched_Queries': lambda x: ', '.join(sorted(set(x)))}
                    for col in meta_cols:
                        agg_dict[col] = 'first'
                    
                    final_df = combined_df.groupby('scan').agg(agg_dict).reset_index()
                    
                    st.success(f"Success! Found {len(final_df)} unique matching scans.")
                    
                    # Display the final results table
                    st.markdown("#### Results Table")
                    st.dataframe(final_df, use_container_width=True)
                    
                    # --- 6. Download Buttons ---
                    # Placed side by side so you can download both the results and the query map
                    dl_col1, dl_col2 = st.columns(2)
                    with dl_col1:
                        csv_data = final_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Results (CSV)",
                            data=csv_data,
                            file_name="massql_results.csv",
                            mime="text/csv",
                        )
                    with dl_col2:
                        queries_csv = queries_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Query Map (CSV)",
                            data=queries_csv,
                            file_name="massql_applied_queries.csv",
                            mime="text/csv",
                        )
                        
            except Exception as e:
                st.error(f"An error occurred during file processing: {e}")