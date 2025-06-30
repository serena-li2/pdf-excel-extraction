import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO

# Your existing regex pattern
ITEM_LINE_RE = re.compile(
    r'^(?P<line_no>\d+)\s+'                              # Line #
    r'(?P<qty>\d+(?:\.\d+)?)\s+'                         # Quantity
    r'(?P<part_id>\S+)\s+'                               # Part ID
    r'\$(?P<unit_price>[\d,]+\.\d{2})\s+'                # Unit Price
    r'\$(?P<ext_price>[\d,]+\.\d{2})$'                   # Extended Price
)

def extract_pdf_invoice(pdf_bytes: bytes) -> pd.DataFrame:
    records = []
    current = None

    # collect all non-blank lines
    lines = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for ln in (page.extract_text() or "").split("\n"):
                ln = ln.strip()
                if ln:
                    lines.append(ln)

    for ln in lines:
        m = ITEM_LINE_RE.match(ln)
        if m:
            current = {
                "Line #":            int(m.group("line_no")),
                "Quantity Ordered":  float(m.group("qty").replace(",", "")),
                "Part ID":           m.group("part_id"),
                "Description":       "",
                "Net Unit Price":    float(m.group("unit_price").replace(",", "")),
                "Net Extended Price": float(m.group("ext_price").replace(",", ""))
            }
            records.append(current)
            continue

        if current and not ln.upper().startswith("LEAD TIME"):
            current["Description"] += (" " + ln) if current["Description"] else ln

    df = pd.DataFrame(records)
    df["Net Extended Price"] = (
        df["Quantity Ordered"] * df["Net Unit Price"]
    ).round(2)

    return df[[
        "Line #",
        "Quantity Ordered",
        "Part ID", 
        "Description",
        "Net Unit Price",
        "Net Extended Price",
    ]]

def main():
    st.title("PDF Invoice to Excel Converter")
    st.write("Upload a PDF invoice to convert it to Excel format")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            df = extract_pdf_invoice(uploaded_file.read())
            
            st.success(f"Successfully extracted {len(df)} items!")
            st.dataframe(df.head())
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            # Create download button
            st.download_button(
                label="Download Excel file",
                data=output.getvalue(),
                file_name="invoice_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()