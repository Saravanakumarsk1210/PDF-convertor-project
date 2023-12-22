import streamlit as st
import pdfplumber
import re
from tabula import read_pdf
import pandas as pd
import base64


def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

def get_download_link(file_path, button_label):
    with open(file_path, 'rb') as file:
        content = file.read()
    st.balloons()
    button_clicked = st.download_button(label=button_label, data=content, file_name=file_path)

def get_error_download_link(error_files, button_label):
    try:
        # Create a text file with the names of the error files
        error_file_path = "error_files.txt"
        with open(error_file_path, "w") as error_file:
            error_file.write("THE ERROR FILES ARE DISPLAYED BELOW!!\nTHIS CONTAINS UNSTRUCTURED DATA. PLEASE DO THESE ENTRIES MANUALLY!! \n.****************************************************************.\n\n")

            for file_name in error_files:
                error_file.write(f"{file_name.name}\n")

        # Generate download link for the error file list
        with open(error_file_path, 'rb') as file:
            content = file.read()
        st.download_button(label=button_label, data=content, file_name=error_file_path)

        # Display the contents of the error file in a colorful text box
        st.text("Contents of Error File:")
        with open(error_file_path, "r") as error_file:
            error_contents = error_file.read()
            st.text(error_contents)

    except Exception as e:
        return f"Error generating download link for error files: {e}"

def process_pdf_code_1(pdf_path, extracted_text):
    awb_match = re.search(r'AWB No: (\d+)', extracted_text)
    awb_no = awb_match.group(1) if awb_match else "Not found"

    non_gst_invoice_match = re.search(r'Non-GST Invoice No:(\S+)', extracted_text)
    non_gst_invoice_no = non_gst_invoice_match.group(1).strip() if non_gst_invoice_match else "Not found"

    non_gst_invoice_date_match = re.search(r'Non-GST Invoice Date: (\d{4}-\d{2}-\d{2})', extracted_text)
    non_gst_invoice_date = non_gst_invoice_date_match.group(1).strip() if non_gst_invoice_date_match else "Not found"

    fob_match = re.search(r'FOB Value in INR:(\S+)', extracted_text)
    fob_value_inr = fob_match.group(1).strip() if fob_match else "Not found"
    dfs = read_pdf(pdf_path, pages="all")
    second_table = dfs[1]
    values = ["Goods Description", "Qty", "Unit Value", "Total Value"]
    Unit = [[] for _ in range(len(values))]
    k = 0

    for i in range(len(values)):
        for column in second_table.columns:
            # Check if the value is present in the column
            if values[i] in second_table[column].values:
                # Find the index where the value is located in the column
                qty_index = second_table[second_table[column] == values[i]].index[0]

                # Store the values in the column starting from the next row
                Unit[k] = second_table.loc[qty_index + 1:, column]

                # Print the values
                k += 1

    for i in range(k):
        float_array = Unit[i]

        # Convert float array to string array
        string_array = [str(value) for value in float_array]

        # Print the result
        Unit[i] = string_array
        names = Unit[i]
        processed_names = [name.replace("\r", "") for name in names]

        # Update the first element of Unit
        Unit[i] = processed_names

    # Placeholder DataFrame for Code 1
    columns = ["Goods Description", "Qty", "Unit Value", "Total Value"]
    df = pd.DataFrame(columns=columns)
    df["Goods Description"] = Unit[0]
    df["Qty"] = Unit[1]
    df["Unit Value"] = Unit[2]
    df["Total Value"] = Unit[3]

    gd = Unit[2][-1]

    # Drop rows with all NaN values
    df = df.drop(df.index[-1])

    return awb_no, non_gst_invoice_no, non_gst_invoice_date, fob_value_inr, gd, df

def process_pdf_code_2(pdf_path, extracted_text):
    pdf_content = extract_text_from_pdf(pdf_path)

    table_match = re.search(r" Goods Description(.+?Total \d+\.\d+)", pdf_content, re.DOTALL)
    table_sentence = table_match.group(0).strip() if table_match else None

    qty_match = re.search(r" PCS (\d+\.\d+)", table_sentence)
    tt_value = qty_match.group(1).strip() if qty_match else None

    unit_value_match = re.search(r" PCS \d+\.\d+ (\d+\.\d+)", table_sentence)
    unit_value = unit_value_match.group(1).strip() if unit_value_match else None

    non_gst_invoice_date_match = re.search(r'Non-GST Invoice Date: (\d{4}-\d{2}-\d{2})', extracted_text)
    non_gst_invoice_date = non_gst_invoice_date_match.group(1).strip() if non_gst_invoice_date_match else "Not found"

    total_value_match = re.search(r"Total (\d+\.\d+)", table_sentence)
    qty_value = total_value_match.group(1).strip() if total_value_match else None

    awb_no_match = re.search(r"AWB No: (\d+)", pdf_content)
    awb_no = awb_no_match.group(1).strip() if awb_no_match else None

    non_gst_invoice_no_match = re.search(r"Non-GST Invoice No:(\d+-\d+)", pdf_content)
    non_gst_invoice_no = non_gst_invoice_no_match.group(1).strip() if non_gst_invoice_no_match else None

    fob_value_match = re.search(r"FOB Value in INR:(\d+\.\d+)", pdf_content)
    fob_value = fob_value_match.group(1).strip() if fob_value_match else None

    extracted_text = pdf_content

    description_match = re.search(r"Goods Description.+? others \d+ \d+ \d+ PCS \d+\.\d+ \d+\.\d+ \d+\.\d+ \d+\.\d+ \d+\.\d+ \d+ \d+\.\d+ \d+\.\d+ INDIA\n(.+?)Total", extracted_text, re.DOTALL)
    product_description = description_match.group(1).strip() if description_match else None
    product_description = str(product_description)
    product_description_combined = product_description.replace('\n', ' ')
    data = {
        "Goods Description": [product_description_combined],
        "Qty": [qty_value],
        "Unit Value": [tt_value],
        "Total Value": [unit_value],
    }
    df = pd.DataFrame(data)

    return awb_no, non_gst_invoice_no, non_gst_invoice_date, fob_value, unit_value, df
def find_awb(pdf_path):
    extracted_text=extract_text_from_pdf(pdf_path)
    awb_match = re.search(r'AWB No: (\d+)', extracted_text)
    awb_no = awb_match.group(1) if awb_match else "Not found"
    return awb_no


def process_pdf(ram_num, pdf_path):

    try:
        dfs = read_pdf(pdf_path, pages="all")
        extracted_text = extract_text_from_pdf(pdf_path)
        num_lines = len(extracted_text.split('\n'))

        if num_lines <= 50:
            awb_no, non_gst_invoice_no, non_gst_invoice_date, fob_value_inr, gd, df = process_pdf_code_2(pdf_path, extracted_text)
        else:
            awb_no, non_gst_invoice_no, non_gst_invoice_date, fob_value_inr, gd, df = process_pdf_code_1(pdf_path, extracted_text)

        result_df = pd.DataFrame({
            "RAMCO No":[ram_num],
            "AWB No": [awb_no],
            "Non-GST Invoice No": [non_gst_invoice_no],
            "Non-GST Invoice Date": [non_gst_invoice_date],
            "FOB Value in INR": [fob_value_inr],
        })

        f = pd.DataFrame({
            "Grand Total": [gd]
        })

        result_df = pd.concat([result_df, df, f], axis=1)

        return result_df
    except Exception as e:
        st.error(f"Error processing {pdf_path}: {e}")
        return None

def main():
    st.title("PDF Data Extraction and CSV Export")
    a = 0
    uploaded_files = st.file_uploader("Upload PDF file(s)", key="file_uploader_key", accept_multiple_files=True)
    error_files = []
    processed_awb_numbers = []

    if uploaded_files:
        ram_num_input = st.text_input("Enter the starting number")
        ram_num = int(ram_num_input) if ram_num_input.strip() else 0
        if not ram_num>0:
            st.write("Enter the Ramco Number correctly")

        if st.button("Extract and Export to CSV") and ram_num>0:
            
            pdf_paths = [uploaded_file for uploaded_file in uploaded_files]
            final_df = pd.DataFrame()

            # Create a text element for displaying the progress
            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, pdf_file in enumerate(pdf_paths, start=1):
                # Dynamically generate a unique key for each iteration
                file_uploader_key = f"file_uploader_{i}"
                pdf_path = pdf_file.name  # Get the file name

                awb_no = find_awb(pdf_file)
                if awb_no in processed_awb_numbers:
                    st.warning(f"Duplicate AWB number ({awb_no}) found in file {pdf_path}. Skipping this file.")
                    continue

                result_df = process_pdf(ram_num, pdf_file)
                a += 1

                # Update the text element with the current value of 'a'
                progress_text.text(f"Processing file {a} of {len(pdf_paths)}")
                progress_bar.progress(i / len(pdf_paths))

                if result_df is not None:
                    processed_awb_numbers.append(awb_no)
                    final_df = pd.concat([final_df, result_df])
                    ram_num += 1
                else:
                    error_files.append(pdf_file)

            if not final_df.empty:
                date = final_df["Non-GST Invoice Date"].values[0]
                csv_file = f'{date} Invoice excel.csv'
                final_df.to_csv(csv_file, index=False)
                st.success(f"Combined output saved to {csv_file}")

                # Download button for Excel file
                get_download_link(csv_file, "Download CSV")

            if error_files !=[]:
                get_error_download_link(error_files, "Download List of Error Files")

if __name__ == "__main__":
    main()
