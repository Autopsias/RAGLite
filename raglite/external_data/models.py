"""Pydantic models for external data sources.

Story 6.1: Tier 1 External Data Source Integration

Models for Portuguese and EU economic data sources:
- INE: Building permits, construction output/cost index
- ATIC: Cement consumption
- BPstat: Mortgage loans
- OMIE: Electricity prices
- EU Oil Bulletin: Diesel prices
- IPMA: Weather data
- Base.gov.pt: Public works contracts
- Commodities: Coal, petcoke, CO2 EUA prices
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataFrequency(str, Enum):
    """Frequency of data updates."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class DataSource(str, Enum):
    """External data source identifiers."""

    INE = "INE"
    ATIC = "ATIC"
    BPSTAT = "BPstat"
    OMIE = "OMIE"
    EU_OIL_BULLETIN = "EU_Oil_Bulletin"
    IPMA = "IPMA"
    BASEGOV = "BaseGov"
    COMMODITIES = "Commodities"


# =============================================================================
# INE (Instituto Nacional de Estatistica) Models
# =============================================================================


class INEBuildingPermits(BaseModel):
    """Building permits data from INE.

    Source: https://www.ine.pt/xportal/xmain?xpgid=ine_api
    Dataset: Licenças de construção
    """

    date: date
    permits_count: int = Field(ge=0, description="Number of building permits issued")
    region: str = Field(default="Portugal", description="Geographic region")
    permit_type: str | None = Field(
        default=None, description="Type of permit (new, renovation, etc.)"
    )
    source: DataSource = Field(default=DataSource.INE)


class INEConstructionOutput(BaseModel):
    """Construction output index from INE.

    Source: https://www.ine.pt/xportal/xmain?xpgid=ine_api
    Dataset: Índice de Produção na Construção
    """

    date: date
    index_value: float = Field(description="Construction output index (base=100)")
    yoy_change_pct: float | None = Field(
        default=None, description="Year-over-year change percentage"
    )
    source: DataSource = Field(default=DataSource.INE)


class INEConstructionCostIndex(BaseModel):
    """Construction cost index from INE.

    Source: https://www.ine.pt/xportal/xmain?xpgid=ine_api
    Dataset: Índice de Custos de Construção de Habitação Nova
    """

    date: date
    total_index: float = Field(description="Total construction cost index")
    materials_index: float | None = Field(default=None, description="Materials cost component")
    labor_index: float | None = Field(default=None, description="Labor cost component")
    source: DataSource = Field(default=DataSource.INE)


# =============================================================================
# ATIC (Cement Industry) Models
# =============================================================================


class ATICCementConsumption(BaseModel):
    """Cement consumption data from ATIC.

    Source: ATIC (Associação Técnica da Indústria de Cimento)
    Note: Data provided via CSV upload, no public API
    """

    date: date
    consumption_tonnes: float = Field(ge=0, description="Cement consumption in tonnes")
    region: str = Field(default="Portugal", description="Geographic region")
    cement_type: str | None = Field(default=None, description="Type of cement (gray, white, etc.)")
    source: DataSource = Field(default=DataSource.ATIC)


# =============================================================================
# BPstat (Banco de Portugal) Models
# =============================================================================


class BPstatMortgageLoans(BaseModel):
    """Mortgage loan data from Banco de Portugal.

    Source: https://bpstat.bportugal.pt/data/v1/
    Dataset: Housing loans to households
    """

    date: date
    total_loans_eur: float = Field(description="Total outstanding mortgage loans (EUR)")
    new_loans_eur: float | None = Field(
        default=None, description="New mortgage loans in period (EUR)"
    )
    avg_interest_rate_pct: float | None = Field(
        default=None, description="Average interest rate percentage"
    )
    source: DataSource = Field(default=DataSource.BPSTAT)


# =============================================================================
# OMIE (Electricity Market) Models
# =============================================================================


class OMIEElectricityPrice(BaseModel):
    """Electricity spot price from OMIE.

    Source: https://www.omie.es/sites/default/files/dados/
    Market: MIBEL (Mercado Ibérico de Electricidade)
    """

    date: date
    hour: int | None = Field(
        default=None, ge=0, le=23, description="Hour of day (0-23) for hourly prices"
    )
    price_eur_mwh: float = Field(description="Electricity price in EUR/MWh")
    market: str = Field(default="MIBEL", description="Electricity market identifier")
    price_type: str = Field(default="spot", description="Price type (spot, futures, etc.)")
    source: DataSource = Field(default=DataSource.OMIE)


# =============================================================================
# EU Oil Bulletin Models
# =============================================================================


class EUDieselPrice(BaseModel):
    """Diesel price from EU Oil Bulletin.

    Source: https://ec.europa.eu/energy/observatory/reports/
    Coverage: Weekly prices for EU member states
    """

    date: date
    price_eur_litre: float = Field(description="Diesel price in EUR per litre")
    country: str = Field(default="Portugal", description="Country code or name")
    tax_included: bool = Field(default=True, description="Whether price includes taxes")
    source: DataSource = Field(default=DataSource.EU_OIL_BULLETIN)


# =============================================================================
# IPMA (Weather) Models
# =============================================================================


class IPMAWeatherData(BaseModel):
    """Weather observation from IPMA.

    Source: https://api.ipma.pt/open-data/
    Coverage: Portugal weather stations
    """

    date: date
    station_id: str = Field(description="Weather station identifier")
    station_name: str | None = Field(default=None, description="Weather station name")
    temperature_c: float | None = Field(default=None, description="Temperature in Celsius")
    temperature_max_c: float | None = Field(
        default=None, description="Maximum temperature in Celsius"
    )
    temperature_min_c: float | None = Field(
        default=None, description="Minimum temperature in Celsius"
    )
    precipitation_mm: float | None = Field(
        default=None, ge=0, description="Precipitation in millimeters"
    )
    humidity_pct: float | None = Field(
        default=None, ge=0, le=100, description="Relative humidity percentage"
    )
    wind_speed_kmh: float | None = Field(default=None, ge=0, description="Wind speed in km/h")
    source: DataSource = Field(default=DataSource.IPMA)


# =============================================================================
# Base.gov.pt (Public Works) Models
# =============================================================================


class BaseGovContract(BaseModel):
    """Public works contract from Base.gov.pt.

    Source: https://www.base.gov.pt/Base4/pt/
    Coverage: Portuguese public procurement contracts
    """

    publication_date: date = Field(description="Contract publication date")
    contract_id: str = Field(description="Unique contract identifier")
    description: str | None = Field(default=None, description="Contract description")
    contract_value_eur: float = Field(ge=0, description="Contract value in EUR")
    contracting_entity: str | None = Field(default=None, description="Public entity name")
    contractor: str | None = Field(default=None, description="Winning contractor name")
    cpv_code: str | None = Field(default=None, description="Common Procurement Vocabulary code")
    execution_location: str | None = Field(
        default=None, description="Location of contract execution"
    )
    source: DataSource = Field(default=DataSource.BASEGOV)


# =============================================================================
# Commodities Models
# =============================================================================


class CommodityPrice(BaseModel):
    """Commodity price data (Coal, Petcoke, CO2 EUA).

    Sources: Various (web scraping targets for manual data entry)
    """

    date: date
    commodity: str = Field(description="Commodity type (coal, petcoke, co2_eua)")
    price: float = Field(ge=0, description="Price value")
    currency: str = Field(default="EUR", description="Price currency")
    unit: str = Field(description="Unit of measurement (tonne, MWh, etc.)")
    source: DataSource = Field(default=DataSource.COMMODITIES)


class CoalPrice(CommodityPrice):
    """Coal price data."""

    commodity: str = Field(default="coal")
    unit: str = Field(default="EUR/tonne")
    grade: str | None = Field(default=None, description="Coal grade/type")


class PetcokePrice(CommodityPrice):
    """Petcoke (petroleum coke) price data."""

    commodity: str = Field(default="petcoke")
    unit: str = Field(default="EUR/tonne")
    sulfur_content_pct: float | None = Field(default=None, description="Sulfur content percentage")


class CO2EUAPrice(CommodityPrice):
    """EU Emissions Trading System (ETS) carbon credit price.

    EUA = European Union Allowance
    """

    commodity: str = Field(default="co2_eua")
    unit: str = Field(default="EUR/tonne")
    market: str = Field(default="EU_ETS", description="Emissions trading system")


# =============================================================================
# Story 6.8: Tier 2 Data Source Models
# =============================================================================


class API2CoalPrice(CommodityPrice):
    """API2 Coal Index price (CIF ARA benchmark).

    Story 6.8 AC1.1: API2 Coal as pet coke proxy (correlation 0.7-0.85)

    API2 is the European thermal coal benchmark for coal delivered
    to Amsterdam-Rotterdam-Antwerp (ARA) ports.

    Used as proxy for pet coke pricing due to high correlation.
    """

    commodity: str = Field(default="api2_coal")
    unit: str = Field(default="USD/tonne")
    benchmark: str = Field(default="API2_CIF_ARA", description="Coal benchmark index")
    petcoke_proxy: bool = Field(
        default=True, description="Indicates this is used as pet coke proxy"
    )


class TTFGasPrice(CommodityPrice):
    """TTF Natural Gas price (European benchmark).

    Story 6.8 AC1.2: TTF Natural Gas for thermal energy forecasting

    TTF (Title Transfer Facility) is the leading European natural
    gas price benchmark, traded on ICE Endex.

    Critical regressor for SECIL thermal energy cost forecasting.
    """

    commodity: str = Field(default="ttf_gas")
    unit: str = Field(default="EUR/MWh")
    market: str = Field(default="TTF", description="Title Transfer Facility (Netherlands)")


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
# Generic Data Point Model (for storage)
# =============================================================================


class ExternalDataPoint(BaseModel):
    """Generic external data point for unified storage.

    Used for PostgreSQL storage in Story 6.2.
    """

    source: DataSource
    indicator: str = Field(description="Data indicator/metric name")
    date: date
    value: float
    unit: str | None = Field(default=None, description="Unit of measurement")
    region: str | None = Field(default=None, description="Geographic region")
    metadata: dict[str, str | float | int | bool | None] = Field(
        default_factory=dict, description="Additional metadata"
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When data was fetched (UTC)",
    )


# =============================================================================
# Story 6.12: Model Weight for Adaptive Ensemble
# =============================================================================


class ModelWeight(BaseModel):
    """Model weight for adaptive ensemble forecasting.

    Story 6.12 AC2: Pydantic model for API interactions with model weights.

    Attributes:
        metric_name: Target metric (e.g., "cement_demand")
        model_name: Model identifier (e.g., "prophet", "xgboost", "catboost")
        weight: Normalized weight (0.0-1.0, sum to 1.0 per metric)
        backtest_rmse: RMSE from rolling backtest validation
        backtest_mape: MAPE from rolling backtest validation
        has_regressors: Whether external regressors were available
        data_points: Number of data points used in backtest
        calculated_at: When weight was last calculated
    """

    metric_name: str = Field(description="Target metric name")
    model_name: str = Field(description="Model identifier")
    weight: float = Field(ge=0.0, le=1.0, description="Normalized weight")
    backtest_rmse: float | None = Field(default=None, description="Backtest RMSE")
    backtest_mape: float | None = Field(default=None, description="Backtest MAPE (%)")
    has_regressors: bool = Field(default=True, description="External regressors available")
    data_points: int | None = Field(default=None, description="Data points in backtest")
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When weight was calculated",
    )


# =============================================================================
# Story 6.14: Model Registry & Retrain Result
# =============================================================================


class ModelRegistry(BaseModel):
    """Model registry entry for trained model checkpoints.

    Story 6.14 AC2: Pydantic model for model registry API interactions.

    Attributes:
        id: Registry entry ID
        model_type: Model type (e.g., "tft", "lstm")
        model_version: Version string (e.g., "v1.0", "2024-12-10")
        checkpoint_path: Path to saved checkpoint file
        metrics_json: Training/validation metrics
        trained_at: When model was trained
        is_active: Whether this is the active checkpoint for this model type
    """

    id: int | None = Field(default=None, description="Registry entry ID")
    model_type: str = Field(description="Model type identifier")
    model_version: str = Field(description="Model version string")
    checkpoint_path: str = Field(description="Path to checkpoint file")
    metrics_json: dict[str, float | str | int] | None = Field(
        default=None, description="Training metrics"
    )
    trained_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When model was trained",
    )
    is_active: bool = Field(default=False, description="Active checkpoint flag")


class RetrainResult(BaseModel):
    """Result of model retraining operation.

    Story 6.14 AC6: MCP tool return type for retrain_forecasting_models.

    Attributes:
        status: Training status ("success", "partial", "failed")
        models_trained: List of model types that were trained
        checkpoint_path: Path to saved checkpoint (if single model)
        metrics: Training/validation metrics summary
        duration_seconds: Training duration
        errors: List of errors encountered (if any)
    """

    status: str = Field(description="Training status")
    models_trained: list[str] = Field(default_factory=list, description="Models trained")
    checkpoint_path: str | None = Field(default=None, description="Checkpoint path")
    metrics: dict[str, float | str] | None = Field(default=None, description="Training metrics")
    duration_seconds: float = Field(description="Training duration")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
