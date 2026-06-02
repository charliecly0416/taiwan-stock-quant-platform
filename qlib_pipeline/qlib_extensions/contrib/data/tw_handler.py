from qlib.contrib.data.handler import Alpha158
from qlib.contrib.data.loader import Alpha158DL


def _tw_alpha158_base_config():
    return Alpha158DL.get_feature_config(
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



def _tw_alpha158_no_std_config():
    fields, names = _tw_alpha158_base_config()
    excluded = {"STD5", "STD10", "STD20", "STD60"}
    kept = [(field, name) for field, name in zip(fields, names) if name not in excluded]
    return [field for field, _ in kept], [name for _, name in kept]


class TWAlpha158Custom(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()

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


class TWAlpha158RetVolOnly(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        custom_fields = [
            "Std($close/Ref($close, 1)-1, 20)",
        ]
        custom_names = [
            "TW_RET_VOL20",
        ]
        return fields + custom_fields, names + custom_names


class TWAlpha158RetVolMA20Gap(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        custom_fields = [
            "Std($close/Ref($close, 1)-1, 20)",
            "Mean($close, 20)/$close - 1",
        ]
        custom_names = [
            "TW_RET_VOL20",
            "TW_MA20_GAP",
        ]
        return fields + custom_fields, names + custom_names



class TWAlpha158NoStd(Alpha158):
    def get_feature_config(self):
        return _tw_alpha158_no_std_config()


class TWAlpha158NoStdRetVol(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_no_std_config()
        custom_fields = [
            "Std($close/Ref($close, 1)-1, 20)",
        ]
        custom_names = [
            "TW_RET_VOL20",
        ]
        return fields + custom_fields, names + custom_names

class TWAlpha158A101020(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        custom_fields = [
            "-1 * Rank($open - Ref($high, 1), 10) * Rank($open - Ref($close, 1), 10) * Rank($open - Ref($low, 1), 10)",
        ]
        custom_names = [
            "A101_020",
        ]
        return fields + custom_fields, names + custom_names


class TWAlpha158Amihud20(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        # This validity guard approximates min_periods for Qlib's rolling Mean. It does
        # not count Ref($close, 1); the only intentional mismatch is each instrument's
        # first row, where amihud_input evaluates to NaN.
        valid = "If($volume > 0, If($vwap > 0, If($close > 0, 1, 0), 0), 0)"
        # Qlib expressions used here do not expose a stable explicit NaN constant, so
        # feature-dependent 0/0 is used as the NaN branch.
        amihud_input = (
            "If($volume > 0, "
            "If($vwap > 0, "
            "If($close > 0, Abs($close / Ref($close, 1) - 1) / (($volume * $vwap) + 1e-12), (($close - $close) / ($close - $close))), "
            "(($close - $close) / ($close - $close))), (($close - $close) / ($close - $close)))"
        )
        custom_fields = [
            f"If(Sum({valid}, 20) >= 10, Mean({amihud_input}, 20), (($close - $close) / ($close - $close)))",
        ]
        custom_names = [
            "TW_AMIHUD20",
        ]
        return fields + custom_fields, names + custom_names


class TWAlpha158IdioSkew60(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        return fields + ["$tw_idio_skew60"], names + ["TW_IDIO_SKEW60"]

class TWAlpha158MarginUtil(Alpha158):
    def get_feature_config(self):
        fields, names = _tw_alpha158_base_config()
        return fields + ["$tw_margin_util"], names + ["TW_MARGIN_UTIL"]

