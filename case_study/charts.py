"""Interactive renderings of the actual notebook calculations and plot recipes."""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from matplotlib.cbook import boxplot_stats
from scipy import stats

PHISH = "#bd5548"
LEGIT = "#2e7197"
INK = "#213a3a"
COLORS = {0: PHISH, 1: LEGIT}  # Original CSV labels.
NAMES = {0: "Phishing", 1: "Legitimate"}


def style(figure, title, x=None, y=None, height=450):
    figure.update_layout(title=dict(text=title, font=dict(size=18, family="Georgia")),
                         height=height, font=dict(family="Segoe UI, Arial", color=INK, size=13),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         margin=dict(l=30, r=24, t=64, b=64),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                         hoverlabel=dict(bgcolor="#ffffff"), barmode="group")
    figure.update_xaxes(title=x, showgrid=False, zeroline=False, automargin=True)
    figure.update_yaxes(title=y, gridcolor="#deded4", zerolinecolor="#a4ada7", automargin=True)
    return figure


def pack(figure):
    return json.loads(figure.to_json())


def histogram(figure, values, bins, name, color, density=False, row=None, col=None):
    counts, edges = np.histogram(np.asarray(values), bins=bins, density=density)
    trace = go.Bar(x=((edges[:-1] + edges[1:]) / 2).tolist(), y=counts.tolist(),
                   width=np.diff(edges).tolist(), name=name, marker_color=color, opacity=0.65,
                   customdata=np.column_stack([edges[:-1], edges[1:]]).tolist(),
                   hovertemplate="%{customdata[0]:.3g}–%{customdata[1]:.3g}<br>%{y:.4g}<extra>%{fullData.name}</extra>")
    figure.add_trace(trace, row=row, col=col)


def box(figure, values, name, color, outliers=False):
    values = np.asarray(values)
    summary = boxplot_stats(values)[0]
    figure.add_trace(go.Box(name=name, q1=[float(summary["q1"])], median=[float(summary["med"])],
                            q3=[float(summary["q3"])], lowerfence=[float(summary["whislo"])],
                            upperfence=[float(summary["whishi"])], marker_color=color, boxpoints=False))
    if outliers:
        fliers = summary["fliers"]
        figure.add_trace(go.Scatter(x=[name] * len(fliers), y=fliers.tolist(), mode="markers",
                                   marker=dict(size=3, opacity=0.18, color=color), showlegend=False,
                                   hovertemplate=f"{name}: %{{y:.3g}}<extra>Sampled outlier</extra>"))
    return summary


def question_chart(number, namespace):
    ns = namespace
    figure = go.Figure()
    if number <= 3:
        labels = {1: "URL length (characters)", 2: "Domain length (characters)", 3: "Number of subdomains"}
        for name, values, color in [("Phishing", ns["phishing_values"], PHISH),
                                     ("Legitimate", ns["legitimate_values"], LEGIT)]:
            box(figure, values, name, color)
            figure.add_trace(go.Scatter(x=[name], y=[float(values.mean())], mode="markers",
                                       marker=dict(symbol="diamond", size=10, color=INK),
                                       name=f"{name} mean", showlegend=False))
        style(figure, f"Q{number}: {labels[number]} by class", "Recorded class", labels[number])
    elif number <= 10:
        figure.add_trace(go.Bar(x=["Phishing", "Legitimate"], y=(100 * ns["presence_rates"]).tolist(),
                               marker_color=[PHISH, LEGIT], text=[f"{v:.2%}" for v in ns["presence_rates"]],
                               textposition="outside", name="Feature present"))
        style(figure, f"Q{number}: feature presence within each class", "Recorded class", "Hosts with feature (%)")
        figure.update_yaxes(range=[0, 110])
    elif number == 11:
        data = ns["tld_summary"]
        figure.add_trace(go.Bar(x=data.TLD.tolist(), y=(data.PhishingRate * 100).tolist(), marker_color=INK,
                               customdata=data[["Hosts", "Phishing"]].values.tolist(),
                               hovertemplate="%{x}<br>Phishing: %{y:.2f}%<br>Hosts: %{customdata[0]:,}<extra></extra>"))
        style(figure, "Q11: recorded phishing fraction by TLD group", "TLD group", "Phishing hosts in group (%)")
    elif number == 12:
        histogram(figure, ns["score_differences"], 40, "Paired score difference", INK)
        figure.add_vline(x=0, line_dash="dash", line_color="#687773")
        figure.add_vline(x=float(ns["score_differences"].mean()), line_color=PHISH)
        style(figure, "Q12: title-score differences on the same phishing hosts", "URL-title minus domain-title score", "Hosts")
    elif number in [13, 14]:
        histogram(figure, ns["shuffled_gaps"], 35, "Shuffled median gaps", INK)
        figure.add_vline(x=float(ns["observed_gap"]), line_color=PHISH, annotation_text="Observed")
        figure.add_vline(x=-float(ns["observed_gap"]), line_color=PHISH, line_dash="dash")
        style(figure, f"Q{number}: permutation null distribution (1,999 shuffles)", "Median gap: phishing minus legitimate", "Shuffles")
    else:
        a, b = ns["rule_a_correct"], ns["rule_b_correct"]
        figure.add_trace(go.Bar(x=["Only A correct", "Only B correct"],
                               y=[int(((a == 1) & (b == 0)).sum()), int(((b == 1) & (a == 0)).sum())],
                               marker_color=[INK, PHISH], textposition="outside"))
        style(figure, "Q15: paired hosts where rule correctness differs", "Paired outcome", "Hosts")
    return pack(figure)


SELECTED_PLOTS = [1, 3, 4, 5, 6, 8, 14, 17, 21, 22, 23, 24]


def eda_chart(number, raw):
    df = raw
    figure = go.Figure()
    sample_note = "All raw source records; repeated URLs and domains retained."
    tables = []
    if number == 1:
        counts = df.label.value_counts().sort_index()
        figure.add_trace(go.Bar(x=[NAMES[i] for i in counts.index], y=counts.tolist(),
                               marker_color=[COLORS[i] for i in counts.index], text=counts.tolist(), textposition="outside"))
        style(figure, "Plot 1: Class Distribution in PhiUSIIL Dataset", "URL class", "Number of URLs")
        figure.update_yaxes(range=[0, float(counts.max()) * 1.18])
    elif number in [3, 4, 5]:
        feature, sample_size, bins = {3: ("URLLength", 7000, 70), 4: ("LineOfCode", 10000, 70), 5: ("NoOfImage", 10000, 60)}[number]
        for label in [1, 0]:
            values = df.loc[df.label == label, feature]
            visible = values[values <= (300 if number == 3 else 200)] if number in [3, 5] else values
            sample = visible.sample(n=min(sample_size, len(visible)), random_state=42).to_numpy()
            sample = np.log1p(sample) if number == 4 else sample
            histogram(figure, sample, bins, NAMES[label], COLORS[label], density=True)
            kde = stats.gaussian_kde(sample.astype(float))
            bandwidth = float(np.sqrt(kde.covariance[0, 0]))
            support = np.linspace(sample.min() - 3 * bandwidth, sample.max() + 3 * bandwidth, 200)
            figure.add_trace(go.Scatter(x=support.tolist(), y=kde(support).tolist(), mode="lines",
                                       line=dict(color=COLORS[label], width=2), name=f"{NAMES[label]} KDE"))
            if number in [3, 4]:
                median = float(values.median())
                figure.add_vline(x=np.log1p(median) if number == 4 else median,
                                line_color=COLORS[label], line_dash="dash")
        x_label = {3: "URL length (values >300 omitted)", 4: "log(Lines of code + 1)", 5: "Number of images (values >200 omitted)"}[number]
        style(figure, f"Plot {number}: {feature} distribution by class", x_label, "Density")
        figure.update_layout(barmode="overlay")
        sample_note = f"Notebook recipe: up to {sample_size:,} rows per class, random_state=42; per-class histogram bins and Scott-bandwidth KDE. " + ("log1p transform." if number == 4 else "Display cutoff only; omitted rows remain in the dataset.")
    elif number == 6:
        grouped = df.groupby(["TLD", "label"]).size().unstack(fill_value=0)
        grouped["Total"] = grouped.sum(axis=1)
        top = grouped.nlargest(15, "Total")
        for label in [1, 0]:
            figure.add_trace(go.Bar(x=top.index.tolist(), y=top[label].tolist(), name=NAMES[label], marker_color=COLORS[label]))
        style(figure, "Plot 6: Top-15 TLDs — Legitimate vs Phishing Count", "Top-level domain", "Number of URLs")
        tables = [{"TLD": str(k), "Legitimate": int(row[1]), "Phishing": int(row[0])} for k, row in top.iterrows()]
    elif number == 8:
        for label in [1, 0]:
            histogram(figure, df.loc[df.label == label, "URLSimilarityIndex"], np.linspace(0, 100, 40),
                      NAMES[label], COLORS[label], density=True)
        style(figure, "Plot 8: URLSimilarityIndex — feature provenance warning", "URL Similarity Index (0–100)", "Density")
        figure.update_layout(barmode="overlay")
    elif number == 14:
        sample = df.sample(40000, random_state=42)
        for label in [0, 1]:
            box(figure, np.log1p(sample.loc[sample.label == label, "NoOfExternalRef"]), NAMES[label], COLORS[label], outliers=True)
        style(figure, "Plot 14: log(NoOfExternalRef + 1) Boxplot", "Class", "log(External references + 1)")
        sample_note = "40,000 raw records, random_state=42; log1p external references. Box statistics use the sample; narrative medians use full raw classes."
    elif number == 17:
        columns = ["URLLength", "DomainLength", "TLDLength", "NoOfSubDomain", "CharContinuationRate",
                   "TLDLegitimateProb", "URLCharProb", "LetterRatioInURL", "NoOfQMarkInURL",
                   "SpacialCharRatioInURL", "LineOfCode", "DomainTitleMatchScore", "URLTitleMatchScore",
                   "NoOfImage", "NoOfCSS", "NoOfJS", "NoOfExternalRef", "NoOfSelfRef", "NoOfEmptyRef", "label"]
        corr = df[columns].corr()
        values = corr.to_numpy().copy()
        values[np.triu_indices_from(values)] = np.nan
        figure.add_trace(go.Heatmap(x=columns, y=columns, z=values.tolist(), colorscale="RdBu_r", zmin=-1, zmax=1,
                                   colorbar=dict(title="Pearson r"), hovertemplate="%{y} / %{x}<br>r=%{z:.3f}<extra></extra>"))
        style(figure, "Plot 17: Correlation Heatmap — Key Numerical Features", "Feature", "Feature", 700)
        figure.update_yaxes(autorange="reversed")
    elif number == 21:
        values = df.URLLength
        q1, q3 = values.quantile([0.25, 0.75])
        lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        outliers = df.loc[(values < lower) | (values > upper)]
        figure = make_subplots(rows=1, cols=2, specs=[[{"type": "xy"}, {"type": "domain"}]],
                               subplot_titles=["URL length with IQR fences (clipped at 300)", "Class mix of flagged rows"])
        histogram(figure, values.clip(upper=300), 100, "URL length", INK, row=1, col=1)
        for cutoff, name in [(q1, "Q1"), (q3, "Q3"), (upper, "Upper fence")]:
            figure.add_vline(x=float(cutoff), line_dash="dash", annotation_text=name, row=1, col=1)
        counts = outliers.label.value_counts()
        figure.add_trace(go.Pie(labels=[NAMES[k] for k in counts.index], values=counts.tolist(),
                               marker_colors=[COLORS[k] for k in counts.index], name="IQR-flagged rows"), row=1, col=2)
        style(figure, "Plot 21: IQR Outlier Detection on URLLength", height=470)
        figure.update_xaxes(title="URL length (clipped at 300)", row=1, col=1)
        figure.update_yaxes(title="Records", row=1, col=1)
        tables = [{"Q1": float(q1), "Q3": float(q3), "IQR": float(q3 - q1), "Lower fence": float(lower),
                   "Upper fence": float(upper), "Flagged records": len(outliers), "Phishing among flagged": float(outliers.label.eq(0).mean())}]
        sample_note += " Clipping is part of the original display recipe, not preprocessing."
    elif number == 22:
        labels = ["Very short (<20)", "Short (20–29)", "Medium (30–49)", "Long (50–99)", "Very long (≥100)"]
        bins = pd.cut(df.URLLength, [0, 20, 30, 50, 100, np.inf], labels=labels, right=False, include_lowest=True)
        counts = df.groupby([bins, df.label], observed=False).size().unstack(fill_value=0).reindex(labels)
        rates = counts[0] / counts.sum(axis=1)
        figure = make_subplots(rows=1, cols=2, subplot_titles=["Record count by URL length bin", "Phishing share within each bin"])
        for label in [1, 0]:
            figure.add_trace(go.Bar(x=labels, y=counts[label].tolist(), name=NAMES[label], marker_color=COLORS[label]), row=1, col=1)
        figure.add_trace(go.Bar(x=labels, y=rates.tolist(), name="Phishing share", marker_color=PHISH), row=1, col=2)
        style(figure, "Plot 22: URL Length Bins — Counts and Phishing Share", height=490)
        figure.update_xaxes(title="URL length category", tickangle=-25)
        figure.update_yaxes(title="Record count", row=1, col=1)
        figure.update_yaxes(title="Phishing share", tickformat=".0%", range=[0, 1.12], row=1, col=2)
        tables = [{"Length bin": str(k), "Phishing": int(row[0]), "Legitimate": int(row[1]), "Phishing share": float(rates.loc[k])} for k, row in counts.iterrows()]
    elif number == 23:
        features = ["URLLength", "DomainLength", "TLDLength", "NoOfSubDomain", "LetterRatioInURL", "SpacialCharRatioInURL", "CharContinuationRate"]
        for label in [1, 0]:
            means, intervals = [], []
            for feature in features:
                values = df.loc[df.label == label, feature]
                z = (values - df[feature].mean()) / df[feature].std(ddof=0)
                means.append(float(z.mean()))
                intervals.append(float(stats.sem(z) * stats.t.ppf(0.975, len(z) - 1)))
            figure.add_trace(go.Bar(x=features, y=means, name=NAMES[label], marker_color=COLORS[label],
                                   error_y=dict(type="data", array=intervals)))
        style(figure, "Plot 23: Standardized Class Means ± 95% CI", "Feature", "Mean in pooled SD units", 490)
        figure.update_xaxes(tickangle=-25)
        sample_note += " Intervals reproduce Plot 23's t-based descriptive intervals, not additional hypothesis tests."
    elif number == 24:
        features = ["IsHTTPS", "HasFavicon", "HasTitle", "HasSocialNet", "HasSubmitButton", "HasHiddenFields",
                    "HasPasswordField", "HasObfuscation", "HasDescription", "HasCopyrightInfo", "Bank", "Pay", "Crypto", "Robots", "IsResponsive"]
        values = [[float(df.loc[df.label == label, feature].mean()) for label in [1, 0]] for feature in features]
        figure.add_trace(go.Heatmap(x=["Legitimate", "Phishing"], y=features, z=values,
                                   text=[[f"{v:.2f}" for v in row] for row in values], texttemplate="%{text}",
                                   colorscale=[[0, "#4c8396"], [0.5, "#f8f5ef"], [1, "#bd5548"]], zmin=0, zmax=1,
                                   colorbar=dict(title="Presence rate")))
        style(figure, "Plot 24: Binary Feature Presence Rate", "Recorded class", "Feature", 640)
        figure.update_yaxes(autorange="reversed")
        tables = [{"Feature": f, "Legitimate": v[0], "Phishing": v[1]} for f, v in zip(features, values)]
    else:
        raise ValueError(f"No notebook plot adapter for Plot {number}")
    return {"figure": pack(figure), "sample_note": sample_note, "table": tables}
