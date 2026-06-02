from qlib.contrib.data.handler import Alpha158
from qlib.contrib.data.loader import Alpha158DL


class TWAlpha158Custom(Alpha158):
    def get_feature_config(self):
        fields, names = Alpha158DL.get_feature_config(
            {
                "kbar": {},
                "price": {
                    "windows": [0],
                    "feature": ["OPEN", "HIGH", "LOW", "VWAP"],
                },
                "volume": {
                    "windows": [0, 1, 2, 5, 10],
                },
                "rolling": {
                    "windows": [5, 10, 20, 60],
                },
            }
        )

        custom_fields = [
            "Mean($close, 20)/$close - 1",
            "Std($close/Ref($close, 1)-1, 20)",
            "Corr($close, Log($volume+1), 20)",
            "Mean($volume, 20)/($volume+1e-12)",
        ]
        custom_names = [
            "TW_MA20_GAP",
            "TW_RET_VOL20",
            "TW_PV_CORR20",
            "TW_VOL_MA20",
        ]
        return fields + custom_fields, names + custom_names
