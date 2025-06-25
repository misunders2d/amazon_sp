import pickle
import pandas as pd
import pandas_gbq

file_path = '/home/misunderstood/Downloads/documents.pkl'

from connection import create_credentials

with open(file_path, 'rb') as f:
    documents = pickle.load(f)


full_df = pd.DataFrame()
all_rows = []
# doc = '3458943020258'
for i, doc in enumerate(documents, start=1):
    if documents[doc] is None:
        print(f'Document {doc} is empty')
    print(f'Processing document {i} of {len(documents)}')
    asin_data = documents[doc]['dataByAsin']
    for asin_row in asin_data:
        temp_df = pd.json_normalize(asin_row)
        temp_df = temp_df.dropna(axis=1, how="all")
        # full_df = pd.concat([full_df, temp_df])
        all_rows.append(temp_df)

# print(full_df.columns)
full_df = pd.concat(all_rows)
full_df.columns = [x.replace('.','_').lower().strip() for x in full_df.columns.tolist()]
print(full_df.shape)
# full_df.to_excel('/home/misunderstood/temp/scp.xlsx',index=False)
pandas_gbq.to_gbq(
    full_df,
    destination_table='mellanni-project-da.auxillary_development.scp_asin_weekly',
    if_exists='append',
    credentials=create_credentials())


combine_query = """
SELECT s.startdate, s.asin, s.impressiondata_impressioncount, d.collection
FROM `mellanni-project-da.auxillary_development.scp_asin_weekly` as s
LEFT JOIN (SELECT DISTINCT(asin), collection FROM `mellanni-project-da.auxillary_development.dictionary`) as d
on s.asin = d.asin

ORDER BY startdate, impressiondata_impressioncount DESC

"""