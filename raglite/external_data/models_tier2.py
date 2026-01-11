"""Tier 2 external data source models and demand-side regressors.

Story 6.8: Tier 2 Data Source Models
Story 6.16: Add Eurostat Construction & Industrial Indicators
Story 6.19: EC Construction Confidence Index
Story 7.0: Electricity Cost Forecasting Fix via REN Integration
Story 7b-7: Demand-Side Regressors for Cement Industry

Models for European and international data sources:
- API2 Coal Index (pet coke proxy)
- TTF Natural Gas
- Eurostat (construction, industrial, housing, permits)
- ENTSO-E Transparency Platform
- REN Data Hub (Portugal electricity)
- EC Business Surveys (construction confidence)
- Demand-side regressors (housing transactions, dwelling completions)
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from .models_base import DataSource

# =============================================================================
# Story 6.8: Tier 2 Data Source Models
# =============================================================================


class API2CoalPrice(BaseModel):
    """API2 Coal Index price (CIF ARA benchmark).

    Story 6.8 AC1.1: API2 Coal as pet coke proxy (correlation 0.7-0.85)

    API2 is the European thermal coal benchmark for coal delivered
    to Amsterdam-Rotterdam-Antwerp (ARA) ports.

    Used as proxy for pet coke pricing due to high correlation.
    """

    date: date
    commodity: str = Field(default="api2_coal")
    price: float = Field(ge=0, description="Price value")
    currency: str = Field(default="USD", description="Price currency")
    unit: str = Field(default="USD/tonne")
    benchmark: str = Field(default="API2_CIF_ARA", description="Coal benchmark index")
    petcoke_proxy: bool = Field(
        default=True, description="Indicates this is used as pet coke proxy"
    )
    source: DataSource = Field(default=DataSource.COMMODITIES)


class TTFGasPrice(BaseModel):
    """TTF Natural Gas price (European benchmark).

    Story 6.8 AC1.2: TTF Natural Gas for thermal energy forecasting

    TTF (Title Transfer Facility) is the leading European natural
    gas price benchmark, traded on ICE Endex.

    Critical regressor for SECIL thermal energy cost forecasting.
    """

    date: date
    commodity: str = Field(default="ttf_gas")
    price: float = Field(ge=0, description="Price value")
    currency: str = Field(default="EUR", description="Price currency")
    unit: str = Field(default="EUR/MWh")
    market: str = Field(default="TTF", description="Title Transfer Facility (Netherlands)")
    source: DataSource = Field(default=DataSource.COMMODITIES)


class EurostatElectricityPrice(BaseModel):
    """Electricity price from Eurostat.

    Story 6.8 AC1.3: Monthly electricity prices for industrial consumers

    Dataset: nrg_pc_204 (electricity prices for industrial consumers)
    Coverage: 2008-present, monthly
    """

    date: date
    price_eur_kwh: float = Field(description="Price in EUR per kWh")
    country: str = Field(default="PT", description="Country code (ISO 2-letter)")
    consumption_band: str = Field(
        default="IC", description="Consumption band (IC = 500-2000 MWh/year)"
    )
    tax_component: str = Field(
        default="X_TAX", description="Tax component (X_TAX = excluding taxes)"
    )


class ENTSOEElectricityPrice(BaseModel):
    """Day-ahead electricity price from ENTSO-E Transparency Platform.

    Story 6.29 P3: Phase 2 - ENTSO-E Integration for Electricity Cost Regressor

    Source: https://transparency.entsoe.eu/
    Coverage: 2015-present, hourly
    Market: European electricity markets
    API: RESTful API with free registration
    """

    date: date
    hour: int | None = Field(
        default=None, ge=0, le=23, description="Hour of day (0-23) for hourly prices"
    )
    price_eur_mwh: float = Field(description="Day-ahead price in EUR per MWh")
    bidding_zone: str = Field(default="PT", description="Market bidding zone (PT, ES, etc.)")
    price_type: str = Field(
        default="day_ahead",
        description="Price type (day_ahead, spot_daily_avg, monthly_avg)",
    )


class RENElectricityPrice(BaseModel):
    """Portuguese electricity spot price from REN Data Hub.

    Story 7.0: Electricity Cost Forecasting Fix via REN Integration

    Source: https://datahub.ren.pt/
    Coverage: 2015-present (daily), sourced from OMIE/MIBEL
    Market: Portuguese electricity market (MIBEL)
    API: RESTful JSON API, no authentication required
    """

    date: date
    hour: int | None = Field(
        default=None, ge=0, le=23, description="Hour of day (0-23) for hourly prices"
    )
    price_eur_mwh: float = Field(description="Electricity price in EUR/MWh")
    price_type: str = Field(
        default="spot",
        description="Price type (spot, daily_avg, monthly_avg)",
    )


class EurostatConstructionOutput(BaseModel):
    """Construction production index from Eurostat.

    Story 6.16 AC1: Construction output index for forecasting

    Dataset: sts_copr_m (Short-term statistics: Production in construction)
    Coverage: 2000-present, monthly
    """

    date: date
    index_value: float = Field(gt=0, description="Index 2021=100")
    country: str = Field(description="ISO 2-letter country code")
    nace_sector: str = Field(description="NACE Rev. 2 sector code")
    seasonal_adjustment: str = Field(description="Seasonal adjustment type (SCA, NSA, WDA)")


class EurostatIndustrialProduction(BaseModel):
    """Industrial production index from Eurostat.

    Story 6.16 AC2: Industrial production index for forecasting

    Dataset: sts_inpr_m (Industrial production)
    Coverage: 2000-present, monthly
    """

    date: date
    index_value: float = Field(gt=0, description="Index 2021=100")
    country: str = Field(description="ISO 2-letter country code")
    nace_sector: str = Field(description="NACE Rev. 2 sector code")
    seasonal_adjustment: str = Field(description="Seasonal adjustment type (SCA, NSA, WDA)")


class EurostatBuildingPermits(BaseModel):
    """Building permits from Eurostat.

    Story 6.18 AC2: Eurostat building permits backup for INE

    Dataset: sts_cobp_m (Building permits - number of dwellings)
    Coverage: 2000-present, monthly
    """

    date: date
    permits_count: int = Field(ge=0, description="Number of building permits")
    country: str = Field(description="ISO 2-letter country code")
    building_type: str = Field(description="Building type (RES, NRES, TOTAL)")


class ECConstructionConfidence(BaseModel):
    """Construction Confidence from EC Business Surveys (via Eurostat).

    Story 6.19: EC Construction Confidence Index

    Dataset: ei_bsbu_m_r2 (Construction confidence indicator and survey results)
    Source: European Commission DG ECFIN
    Coverage: 1980-present, monthly
    Indicators:
    - BS-CCI-BAL: Construction confidence indicator (main)
    - BS-CEME-BAL: Employment expectations over next 3 months
    - BS-COB-BAL: Evolution of current order books
    """

    date: date
    confidence_index: float = Field(description="Construction confidence indicator (BS-CCI-BAL)")
    employment_expectations: float | None = Field(
        None, description="Employment expectations over next 3 months (BS-CEME-BAL)"
    )
    order_books: float | None = Field(
        None, description="Evolution of current order books (BS-COB-BAL)"
    )
    country: str = Field(description="ISO 2-letter country code")


class INEHousePriceIndex(BaseModel):
    """House Price Index from INE.

    Story 6.8 AC2.1: Leading indicator for construction demand

    Dataset: 0010017 (Índice de Preços da Habitação)
    """

    date: date
    index_value: float = Field(description="House price index value (base=100)")
    yoy_change_pct: float | None = Field(
        default=None, description="Year-over-year change percentage"
    )
    region: str = Field(default="Portugal", description="Geographic region")


class INEConstructionConfidence(BaseModel):
    """Construction Confidence Indicator from INE.

    Story 6.8 AC2.1: Sentiment indicator for construction sector

    Dataset: 0011127 (Indicador de Confiança da Construção)
    """

    date: date
    confidence_index: float = Field(description="Construction confidence index")
    region: str = Field(default="Portugal", description="Geographic region")


class BPstatBankAppraisal(BaseModel):
    """Bank appraisal values from Banco de Portugal.

    Story 6.8 AC2.2: Leading indicator for construction financing

    BPstat series: 12559916 (average bank appraisal values for housing)
    """

    date: date
    avg_appraisal_eur_m2: float = Field(description="Average appraisal value in EUR per m²")
    region: str = Field(default="Portugal", description="Geographic region")


# =============================================================================
# Story 7b-7: Demand-Side Regressors for Cement Industry
# =============================================================================


class EurostatHousingTransactions(BaseModel):
    """Housing market activity data from Eurostat prc_hpi_q.

    Story 7b-7 AC1: Demand-side regressor for cement industry forecasting.

    Dataset: prc_hpi_q (House Price Index, quarterly, 2015=100)
    Source: INE Portugal via Eurostat
    Coverage: Quarterly, 2005-present for Portugal
    Frequency: Quarterly (Q1, Q2, Q3, Q4)

    House Price Index is a proxy for housing market activity and cement demand:
    - Rising prices indicate strong demand -> construction -> cement consumption
    - 6-12 month lag between price growth and cement demand

    Note: The field is named transaction_count for backward compatibility,
    but stores index values (typically 150-280 range for Portugal).
    """

    date: date
    transaction_count: int = Field(ge=0, description="House Price Index value (2015=100)")
    country: str = Field(default="PT", description="ISO 2-letter country code")
    period: str = Field(description="Original period string (e.g., '2024-Q3')")


class EurostatDwellingCompletions(BaseModel):
    """Dwelling completion data from INE Portugal / Eurostat.

    Story 7b-7 AC2: Lagging demand indicator for construction activity.

    Source: INE Portugal (Statistics Portugal)
    Coverage: Quarterly, 1971-present
    Frequency: Quarterly

    Dwelling completions are a lagging indicator:
    - Completions follow permits by 12-24 months
    - Indicates actual construction activity completion
    """

    date: date
    completion_count: int = Field(ge=0, description="Number of dwellings completed in quarter")
    country: str = Field(default="PT", description="ISO 2-letter country code")
    dwelling_type: str = Field(
        default="TOTAL", description="Dwelling type (TOTAL, RES=residential, NRES=non-residential)"
    )
