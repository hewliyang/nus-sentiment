import streamlit as st
import pandas as pd
import pinecone
import requests
from utils.semantics import download_sentence_embedder
from components.post_card import display_post, paginator
from components.charts import pie, line_and_scatter

st.set_page_config(layout="wide", page_icon="📈", page_title="Semantic Search")

# init pinecone session
pinecone.init(
    api_key=st.secrets["PINECONE_KEY"],
    environment="us-west1-gcp"
)

# init retriever
retriever = download_sentence_embedder()

index_name = "nus-sentiment" ## replace later

# check if the sentiment-mining index exists
if index_name not in pinecone.list_indexes():
    # create the index if it does not exist
    pinecone.create_index(
        index_name,
        dimension=384,
        metric="cosine"
    )

index = pinecone.Index(index_name)

##############################################################################################
### UI Start
##############################################################################################

hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        code, h1 {color: #ff5138;}
        h3, p {color: #fff;}
        footer {visibility: hidden;}
        input {color: #fff !important;}
        button:hover {background-color: #ff5138;}
        button:focus {box-shadow: #ff5138;}
        </style>
        <h1>Semantic Search</h1>
        """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

st.info('''
Unsatisfied with the results? Help us by heading the the **Search** page and inputting a related keyword to gather more data!
''', icon="ℹ️")

PINECONE_API_KEY = st.secrets["PINECONE_KEY"]
try:
    stats = requests.get("https://nus-sentiment-a01055d.svc.us-west1-gcp.pinecone.io/describe_index_stats",
        headers={"Api-Key":PINECONE_API_KEY})
    fullness = stats.json()["indexFullness"]
    total_entries = stats.json()["totalVectorCount"]
    st.markdown("### Database Statistics")
    st.markdown(f"###### Fullness [0,1] : {fullness}")
    st.markdown(f"###### Total Posts : {total_entries}")
except:
    pass

with st.form("Semantic Search [Fast!]"):
    query = st.text_input(label="Input your query here", placeholder="Is CS1010S a very difficult subject?")
    top_k_matches = st.number_input(label="Return the top K matches", min_value=1, max_value=500, value=10)
    submitted = st.form_submit_button("Submit")

    if not query:
        st.stop()

# generate dense vector embeddings for the query
xq = retriever.encode(query).tolist()
# query pinecone
result = index.query(xq, top_k=top_k_matches, include_metadata=True)

matches = result["matches"]
meta = [post["metadata"] for post in matches]

with st.expander("View matches"):
    for post in paginator(meta, 5):
        display_post(post)

# get counts dictionary
def count_sentiment(meta):
    sentiments = {"negative": 0, "neutral": 0, "positive": 0}
    for post in meta:
        if post["sentiment"] > 0:
            sentiments["positive"] += 1
        elif post["sentiment"] < 0:
            sentiments["negative"] += 1
        else:
            sentiments["neutral"] += 1
    return sentiments

d = count_sentiment(meta)
sentiment_data = pd.DataFrame({"name": list(d.keys()), "value": list(d.values())})

c1,c2,c3,c4=st.columns([2,4,4,2], gap="large")
with c2:
    pie = pie(sentiment_data)
    st.altair_chart(pie)
with c3:    
    line = line_and_scatter(data=pd.DataFrame(meta), keyword=query)
    st.altair_chart(line)
