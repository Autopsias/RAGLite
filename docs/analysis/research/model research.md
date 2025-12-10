For a cement manufacturing use case, you should not rely on a single model. Instead, you should architect a **"Cascade System"** where operational outputs feed into financial forecasts. The physical constraints of a kiln (physics) drive your costs (finance), so your models must reflect this dependency.

Here is the targeted recommendation for your stack:

### 1. Operational KPIs (The "Physics" Layer)
**Goal:** Forecast Kiln Heat Rate, Clinker Quality (C3S levels), and Energy Consumption (kWh/ton).
**The Edge:** **CatBoost** or **XGBoost**.

*   **Why:** Cement data is tabular but physically complex (temperatures, feed rates, fan speeds).
*   **The "Edge":**
    *   **Handling Non-Linearity:** The relationship between fuel mix (e.g., petcoke vs. tires) and kiln temperature is highly non-linear. Tree-based gradient boosting (specifically CatBoost) has shown up to **0.90 R² accuracy** in predicting cement mill energy consumption, often outperforming deep learning for this specific tabular data.[1][2]
    *   **Robustness:** Unlike neural networks, these models don't fail catastrophically if a sensor goes offline (which happens often in plants); they handle missing values natively.
    *   **Recommendation:** Use **CatBoost** specifically because it handles categorical variables (like "Fuel Type A" vs "Fuel Type B") better than XGBoost without extensive preprocessing.

### 2. Financial KPIs (The "Business" Layer)
**Goal:** Forecast Cost Per Ton, EBITDA, and Carbon Credits (ETS) usage.
**The Edge:** **Temporal Fusion Transformer (TFT)**.

*   **Why:** Financial KPIs in heavy industry are "Multivariate" problems. Your cost isn't just a time series; it is `Time + Energy Price + Operational Efficiency + Production Volume`.
*   **The "Edge":**
    *   **Interpretability:** TFT is a deep learning model designed by Google/Oxford that tells you *why* a forecast changed. It can explicitly tell you: *"EBITDA is forecast to drop next week primarily because of the 'Coal Price' variable, not the 'Production Volume' variable."*.[3]
    *   **Variable Selection:** It automatically learns which inputs matter. If you feed it "Rainfall," "Coal Price," and "Shift Manager ID," it will learn that "Rainfall" impacts "Quarry Output" (wet raw meal) but not "Kiln Fuel Efficiency."

### 3. The "Zero-Shot" Benchmark
**Goal:** Quick forecasts for demand, sales, or macro-economic trends.
**The Edge:** **Chronos (Amazon)** or **TimesFM (Google)**.

*   **Why:** These are "Time Series Foundation Models" (TSFMs) pre-trained on billions of data points.
*   **The "Edge":** You can use these *without training*. If you need to quickly ask, "What does the construction market demand look like for the next 6 months based on these 3 years of history?", these models can give you a high-quality baseline instantly, acting as a sanity check for your custom models.[4][5]

### Architectural Recommendation: The "Digital Twin" Cascade
To get the true "edge" in your architecture, link these models sequentially rather than in parallel.

1.  **Step 1 (Physics Model):** Use **CatBoost** to predict *Operational KPIs* (e.g., "Given the maintenance schedule, we will consume 400GWh of power next month").
2.  **Step 2 (Financial Model):** Feed that 400GWh prediction as a *feature* into your **TFT** model to predict *Financial KPIs* (e.g., "At current hedged prices, 400GWh = €X cost").

### Summary Table for Your Architect

| KPI Type | Recommended Model | Why it wins |
| :--- | :--- | :--- |
| **Kiln/Mill Energy (kWh)** | **CatBoost** | Handles dirty sensor data & non-linear physics best [1]. |
| **Costs / Margins (€)** | **Temporal Fusion Transformer** | Explains *drivers* (price vs. volume) of financial variance [3]. |
| **Market Demand** | **Chronos (Small/Base)** | Zero-shot capability; no training pipeline needed [6]. |
| **Clinker Quality** | **TCN (Temporal ConvNet)** | Captures the "lag" in the kiln (4-6 hour residence time) better than RNNs [7]. |

[1](https://www.nature.com/articles/s41598-025-03232-z)
[2](https://www.nature.com/articles/s41598-025-10641-7)
[3](https://ceur-ws.org/Vol-4064/SENTIS-paper3.pdf)
[4](https://research.aimultiple.com/time-series-foundation-models/)
[5](https://www.pricepedia.it/en/magazine/article/2025/11/07/the-arrival-of-foundation-models-in-time-series-forecasting/)
[6](https://arxiv.org/html/2504.04011v1)
[7](https://thermalscience.rs/pdfs/papers-2024/TSCI240318168W.pdf)
[8](https://www.nature.com/articles/s41598-025-10342-1)
[9](https://www.sciencedirect.com/science/article/pii/S0952197625021980)
[10](https://arxiv.org/html/2412.11981v1)
[11](https://www.jsetms.com/admin/uploads/YA8vRa.pdf)
[12](https://www.nature.com/articles/s44172-025-00432-3)
[13](https://pmc.ncbi.nlm.nih.gov/articles/PMC12103584/)
[14](https://www.reddit.com/r/datascience/comments/xw8fs6/is_xgboost_the_best_model_out_there_for_time/)
[15](https://ajme.ro/PDF_AJME_2025_3/L6.pdf)
[16](https://aiche.onlinelibrary.wiley.com/doi/10.1002/amp2.10137)
[17](https://ijisrt.com/a-machine-learning-approach-to-improve-the-cement-manufacturing-process-by-optimising-the-time-for-quality-checking)
[18](https://www.sciencedirect.com/science/article/pii/S073658452500064X)
[19](https://www.nature.com/articles/s41598-022-11429-9)
[20](https://otexts.com/fpppy/nbs/15-foundation-models.html)

Now let me create a structured comparison for your cement company use case.

## Comprehensive Model Comparison for Financial KPI Forecasting

For cement manufacturing financials, this is a **"choose your tradeoff"** decision. Here is the practical breakdown:

### 1. XGBoost / LightGBM + HierarchicalForecast (Your "Safe Bet")

| Aspect | Rating | Notes |
| :--- | :--- | :--- |
| **Accuracy** | ⭐⭐⭐⭐ | Outperforms Prophet significantly on tabular financial data [1][2]. Best for cost-driver interaction (fuel price × volume) [3]. |
| **Explainability** | ⭐⭐⭐⭐⭐ | Feature importance is straightforward. Finance teams understand "this variable mattered 40%" [2]. |
| **Interpretability** | ⭐⭐⭐ | No temporal decomposition plots like Prophet, but you get SHAP values showing individual prediction drivers. |
| **Training Data Required** | ⭐⭐⭐⭐⭐ | Works with 12-24 months of data (the typical cement KPI history) [2]. |
| **Deployment Complexity** | ⭐⭐⭐⭐⭐ | Simple. Just pickle the model, run inference in milliseconds on CPU. No GPU needed. |
| **Hierarchical Consistency** | ⭐⭐⭐⭐⭐ | Use HierarchicalForecast to ensure Plant forecasts sum to Region, Region to Company [4][5]. |

**Recommendation:** Start here. It will likely beat Prophet by 15-25% in MAPE on cement financial KPIs, and your CFO will understand the drivers.

***

### 2. NeuralProphet (Your "Incremental Upgrade")

| Aspect | Rating | Notes |
| :--- | :--- | :--- |
| **Accuracy** | ⭐⭐⭐⭐ | Better than Prophet, but typically loses to XGBoost by 5-10% on tabular financial data [6][7]. |
| **Explainability** | ⭐⭐⭐⭐ | Keeps Prophet's "Trend + Seasonality" decomposition plots, adds AR-Net layer [6][7]. |
| **Interpretability** | ⭐⭐⭐ | Better than deep learning, but still harder to explain than tree models. |
| **Training Data Required** | ⭐⭐⭐⭐ | Needs ~24 months minimum. Less tolerant of sparse data than XGBoost [6]. |
| **Deployment Complexity** | ⭐⭐⭐ | Moderate. PyTorch dependency, requires some infra. |
| **Why to Pick It** | Best for "Prophet-like" interpretability but you want neural network power. Good middle ground. |

**When to Use:** If your team is already comfortable with Prophet and wants better accuracy without scrapping the whole approach.

***

### 3. Temporal Fusion Transformer (Your "SOTA But Risky" Option)

| Aspect | Rating | Notes |
| :--- | :--- | :--- |
| **Accuracy** | ⭐⭐⭐⭐⭐ | Outperforms XGBoost on **multivariate** problems where you have many external features (Energy Price, Fuel Mix, Maintenance Events) [8][9][10]. Produces **quantile forecasts** (P10, P50, P90) which beats point estimates [11]. |
| **Explainability** | ⭐⭐⭐⭐ | Attention weights tell you which variables mattered and *when* they mattered (temporal attention) [9][12]. |
| **Interpretability** | ⭐⭐⭐⭐ | Shows feature importance *dynamically* through time. E.g., "Coal Price mattered in Jan-Mar, but Volume matters Apr-Dec." [9][12]. |
| **Training Data Required** | ⭐⭐⭐ | Needs 18+ months ideally. Sensitive to hyperparameter tuning. Requires careful feature engineering [11][2]. |
| **Deployment Complexity** | ⭐⭐ | Moderate-to-High. PyTorch, GPU recommended (though CPU is doable for cement KPIs). Sequence padding/masking to manage. |
| **Production Risk** | ⭐⭐⭐ | "Black box" transformer. Hard to debug if it fails. Needs continuous retraining [11]. |
| **Hierarchical Consistency** | ⭐⭐ | Not natively designed for hierarchical reconciliation. You'd have to add that layer separately. |

**Critical Note:** TFT shines on **multivariate, high-dimensional** data (many external features). If your cement financial KPI is just "Cost Per Ton = f(Energy Price, Raw Material Price, Volume, Quality)" with 5-10 features, XGBoost will likely tie or beat TFT with 10% of the complexity.[8][2]

**When to Pick It:** Only if you have 30+ external time-series features (e.g., fuel prices, labor indices, market demand, logistics costs). Then its attention mechanism learns which combinations matter.

***

### 4. Chronos (Your "Future-Proof Option")

| Aspect | Rating | Notes |
| :--- | :--- | :--- |
| **Accuracy (Zero-Shot)** | ⭐⭐⭐⭐ | Impressive without fine-tuning. Often beats task-specific models on unseen domains [13]. |
| **Accuracy (Fine-Tuned)** | ⭐⭐⭐⭐⭐ | Fine-tuned Chronos-Small beats ALL models (including TFT) when trained on your cement data [13]. |
| **Explainability** | ⭐ | Black box. You get a forecast, not "why." Not audit-friendly for finance. |
| **Training Data Required** | ⭐⭐⭐⭐ | Works zero-shot with minimal data. Fine-tuning is efficient (small footprint). |
| **Deployment Complexity** | ⭐⭐⭐⭐⭐ | Simple. Model is small (Tiny ~130M, Large ~710M params). CPU inference is fast [13]. |
| **The Catch** | ⭐ | **Fine-tuning sometimes *hurts* performance on your domain** if you don't have enough data or the data distribution differs from training corpus [14][15]. |

**Critical Finding:** Research shows **feature-engineered XGBoost consistently beats Chronos** when you have domain knowledge and proper feature engineering. Chronos wins when you have zero domain knowledge and minimal data.[15]

**When to Pick It:** Forecasting new product lines or markets where you have little historical data (e.g., entering a new geography). Chronos' pre-training gives you a baseline instantly.

***

## Architecture Recommendation for Cement Financial KPIs

**Tier 1 (Immediate Deployment - 2 weeks):**
Use **XGBoost + HierarchicalForecast** because:
- Your cement data is tabular (cost drivers, volumes, prices).
- You likely have 2-3 years of monthly financial data (enough for XGBoost).
- Hierarchical reconciliation ensures Plant → Region → Company forecasts are consistent (critical for board reporting).
- Explainability: "Cost rose 8% next month because Coal Price went up 12%, offsetted by 4% Volume decrease."

**Tier 2 (Refinement - 6-8 weeks):**
Prototype **Temporal Fusion Transformer** if:
- You have >30 external time-series features from your DCS/ERP (fuel composition, energy real-time, logistics costs, labor indices).
- You want **probabilistic forecasts** (EBITDA forecast: 5M€ [P10], 5.5M€ [P50], 6M€ [P90]) for risk management.
- You can afford 1-2 GPU weeks for experimentation.

**Tier 3 (Scale-Out - 3+ months):**
Consider **Chronos fine-tuned** if:
- You want a production-grade foundation model that works across all your cement plants globally.
- You plan to forecast dozens of KPIs (not just financials) with a single model architecture.

**Skip NeuralProphet** unless you want to keep the "Prophet mental model" with slightly better accuracy—it's the middle ground between your current system and a real upgrade.

***

### The Real "Edge" for Your Architecture

The practical edge comes from **hierarchical + regressors**, not the model algorithm itself:

1. **Regressor Selection:** Include leading indicators (Cement Market Index, Energy Futures, Construction Permits) 3-6 months ahead of your actual costs.
2. **Hierarchical Reconciliation:** Forecast bottom-up (kiln-line level) and then reconcile, as plant-level anomalies are often predictable.
3. **Ensemble:** Combine XGBoost base + Chronos zero-shot as a sanity check. If they diverge >10%, investigate the data.

This beats any single "SOTA" model for finance work.

[1](http://www.diva-portal.org/smash/get/diva2:1887941/FULLTEXT01.pdf)
[2](https://www.reddit.com/r/MachineLearning/comments/vpkpa2/d_recurrent_neural_network_vs_gradient_boosting/)
[3](https://pdfs.semanticscholar.org/a2fe/b9449a99907a9ad301c0936d2e29472ace47.pdf)
[4](https://robjhyndman.com/papers/Foresight-hts-final.pdf)
[5](https://unit8.com/resources/hierarchical-forecast-reconciliation-with-darts/)
[6](https://www.journeyfurther.com/articles/better-forecasting-with-neuralprophet)
[7](https://bytepawn.com/comparing-neuralprophet-and-prophet-for-timeseries-forecasting.html)
[8](https://www.reddit.com/r/MachineLearning/comments/t9ou4z/d_do_we_really_need_deep_learning_models_for_time/)
[9](https://www.alphaxiv.org/overview/1912.09363v3)
[10](https://www.sciencedirect.com/science/article/pii/S259012302400029X)
[11](https://www.reddit.com/r/MachineLearning/comments/18ax51t/d_transformers_for_time_series_forecasting/)
[12](https://zaai.ai/tft-an-interpretable-transformer/)
[13](https://arxiv.org/html/2403.07815v1)
[14](https://github.com/amazon-science/chronos-forecasting/discussions/143)
[15](https://arxiv.org/html/2508.20437v1)
[16](https://zaai.ai/chronos-the-rise-of-foundation-models-for-time-series-forecasting/)
[17](https://pmc.ncbi.nlm.nih.gov/articles/PMC9026292/)
[18](https://arxiv.org/html/2507.08858v1)
[19](https://www.arxiv.org/pdf/2508.04048.pdf)
[20](https://www.informatica.si/index.php/informatica/article/viewFile/3826/2747)
[21](https://www.internationaljournalssrg.org/IJECE/2024/Volume11-Issue11/IJECE-V11I11P117.pdf)
[22](https://www.linkedin.com/posts/ghoshaltanmoy_additionalkpi-cement-activity-7337744882154840064-pGKz)
[23](https://cienciadedatos.net/documentos/py49-modelling-time-series-trend-with-tree-based-models.html)
[24](https://www.sciencedirect.com/science/article/pii/S2666546825000618)
[25](https://www.academia.edu/143975690/SMART_MAINTENANCE_IN_MEDICAL_IMAGING_MANUFACTURING_TOWARDS_INDUSTRY_4_0_COMPLIANCE_AT_CHRONOS_IMAGING)
[26](https://ieeexplore.ieee.org/iel8/10560474/10561254/10561261.pdf)
