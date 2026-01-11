"""ECB API configuration and constants.

Story 8.2 Task 5: ECB client refactoring
"""

# ECB SDMX API Configuration
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# ECB SDMX series keys for EURIBOR
# Format: FM.M.U2.EUR.RT.MM.EURIBOR{tenor}D_.HSTA
# HSTA = Historical close, average of observations through period
EURIBOR_SERIES = {
    "3M": "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
    "6M": "M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
    "12M": "M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA",
}

# Story 6.17 AC1: GDP growth series key template
# Story 6.24: Fixed series key to match ECB Data Portal format
# Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY
# Q = Quarterly, Y = Year-on-year, B1GQ = GDP at market prices
# EUR = Euro currency, LR = Chain linked volume, GY = Growth year-on-year
# Working example: MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY
GDP_SERIES_TEMPLATE = "Q.Y.{country}.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY"

# Story 6.17 AC2: HICP series key template
# M.{country}.N.000000.4.INX
# M = Monthly, 000000 = All items, 4 = Index, INX = Index level
HICP_SERIES_TEMPLATE = "M.{country}.N.000000.4.INX"
