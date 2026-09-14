import streamlit as st
from ui_common import page_setup, load, eyebrow
from analytics import correlate

page_setup("Correlations")
data = load()
vids, media = data["videos"], data["ig_media"]

st.title("Correlations")
eyebrow("What actually predicts performance")

st.subheader("YouTube — video traits vs views")
yc = correlate.youtube_correlations(vids)
if yc.empty:
    st.caption("Need at least ~4 tracked videos.")
else:
    st.dataframe(yc, use_container_width=True, hide_index=True)
    st.caption("Spearman r: +1 = more of this trait goes with more views, "
               "-1 = the reverse, 0 = no relationship.")

st.divider()
st.subheader("Instagram — content type vs reach")
ic = correlate.instagram_correlations(media)
if ic["by_type"].empty:
    st.caption("Need some tracked Instagram posts.")
else:
    st.dataframe(ic["by_type"], use_container_width=True, hide_index=True)
    top = ic["by_type"].iloc[0]
    st.markdown(f"**Takeaway:** *{top['media_type']}* is your highest-reach format "
                f"(~{int(top['avg_score']):,} avg). Weight your posting toward it.")
