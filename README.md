# Department Of Phisheries

Statistical and exploratory analysis of the PhiUSIIL phishing URL dataset using a Jupyter notebook.

## Files

- `Department_Of_Phisheries.ipynb`: Main notebook with preprocessing, EDA, probability modeling, PCA, and CLT analysis.
- `PhiUSIIL_Phishing_URL_Dataset.csv`: Primary dataset used by the notebook.
- `PhiUSIIL_Phishing_URL_Dataset_copy.csv`: Dataset copy.

## Project Highlights

- Data cleaning, encoding, scaling, and PCA-based dimensionality study.
- 15 focused analysis questions comparing phishing vs legitimate URLs.
- Statistical testing (Welch t-test, chi-square, KS tests) and distribution fitting.
- Central Limit Theorem demonstration through repeated sampling.

## How To Run

1. Open `Department_Of_Phisheries.ipynb` in VS Code with Jupyter extension.
2. Ensure Python environment has required packages: `numpy`, `pandas`, `matplotlib`, `seaborn`, `scipy`, `scikit-learn`.
3. Run cells top-to-bottom to reproduce all outputs and plots.

## Key Takeaway

The notebook shows strong separability between classes through behavioral and structural URL/page features, with `URLSimilarityIndex`, title-match scores, HTTPS usage, and social-link presence emerging as especially informative indicators in this dataset.
