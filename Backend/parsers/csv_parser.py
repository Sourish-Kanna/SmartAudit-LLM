import pandas as pd

def parse_csv(file_path):
    """
    Parses a CSV file and returns a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(f"Error parsing CSV file: {e}")
        return None

def df_to_invoices(df):
    """
    Converts a DataFrame to a list of invoice dictionaries.
    Assumes the DataFrame has columns: invoice_id, vendor, date, product, quantity, unit_price, total.

    Args:
        df (pandas.DataFrame): DataFrame containing invoice data.

    Returns:
        list: A list of invoice dictionaries, each with a list of products.
    """
    invoices = []
    if df is None or df.empty:
        return invoices

    # Group by invoice_id, vendor, date to collect products per invoice
    group_cols = ['invoice_id', 'vendor', 'date']
    required_cols = group_cols + ['product', 'quantity', 'unit_price', 'total']
    if not all(col in df.columns for col in required_cols):
        return invoices

    grouped = df.groupby(group_cols)
    for (invoice_id, vendor, date), group in grouped:
        products = []
        for _, row in group.iterrows():
            product = {
                "name": row['product'],
                "quantity": row['quantity'],
                "unit_price": row['unit_price'],
                "total": row['total']
            }
            products.append(product)
        invoice = {
            "invoice_id": invoice_id,
            "vendor": vendor,
            "date": date,
            "products": products
        }
        invoices.append(invoice)
    return invoices

def csv_parser(file_path):
    """
    Parses a CSV file and converts it to a list of invoice dictionaries.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        list: A list of dictionaries representing invoices.
    """
    df = parse_csv(file_path)
    if df is not None:
        return df_to_invoices(df)
    return []

# Example usage:
if __name__ == "__main__":
    import pprint
    invoices = csv_parser('./sample_data/test1.csv')
    pprint.pprint(invoices, indent=2)