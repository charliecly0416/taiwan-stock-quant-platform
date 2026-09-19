---
created_at: 2026-06-29T13:15:13+00:00
status: candidate_validation_failed
scope: option_c_yahoo_scrapling_staged_refresh_report
---

# Option C Yahoo Scrapling Staged Refresh Report

## Summary

- job_id: `dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy`
- status: `candidate_validation_failed`
- asof: `2026-06-26`
- job_dir: `/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy`
- universe_count: `150`
- proxy_used: `False`
- fetch_status: `fail`
- symbols_success: `0` / `150`
- normalized_validation: `fail`
- provider_validation: `not_run`
- model_smoke: `not_run`
- formal_provider_mutated: `False`
- latest_signal_updated: `False`

## Fetch

```json
{
  "status": "fail",
  "source": "Yahoo Finance chart API via Scrapling",
  "source_policy": "Yahoo-only; no yfinance; no FinMind fallback; no mixed provider",
  "start": "2015-01-01",
  "end": "2026-06-26",
  "proxy_used": false,
  "proxy": "",
  "sleep_seconds": 0.5,
  "symbols_expected": 150,
  "symbols_success": 0,
  "symbols_empty": [
    "TW1301",
    "TW1303",
    "TW1326",
    "TW1519",
    "TW1560",
    "TW1590",
    "TW1605",
    "TW1711",
    "TW1717",
    "TW1785",
    "TW1802",
    "TW1815",
    "TW2049",
    "TW2059",
    "TW2301",
    "TW2303",
    "TW2308",
    "TW2313",
    "TW2317",
    "TW2324",
    "TW2327",
    "TW2330",
    "TW2337",
    "TW2344",
    "TW2345",
    "TW2357",
    "TW2360",
    "TW2367",
    "TW2368",
    "TW2376",
    "TW2379",
    "TW2382",
    "TW2383",
    "TW2404",
    "TW2408",
    "TW2409",
    "TW2412",
    "TW2449",
    "TW2451",
    "TW2454",
    "TW2455",
    "TW2467",
    "TW2481",
    "TW2485",
    "TW2486",
    "TW2489",
    "TW2492",
    "TW2603",
    "TW2609",
    "TW2881",
    "TW2882",
    "TW2887",
    "TW2891",
    "TW3006",
    "TW3008",
    "TW3017",
    "TW3030",
    "TW3034",
    "TW3036",
    "TW3037",
    "TW3044",
    "TW3081",
    "TW3105",
    "TW3131",
    "TW3163",
    "TW3167",
    "TW3189",
    "TW3211",
    "TW3231",
    "TW3260",
    "TW3264",
    "TW3293",
    "TW3324",
    "TW3363",
    "TW3374",
    "TW3376",
    "TW3443",
    "TW3450",
    "TW3481",
    "TW3491",
    "TW3529",
    "TW3533",
    "TW3563",
    "TW3583",
    "TW3653",
    "TW3661",
    "TW3665",
    "TW3693",
    "TW3702",
    "TW3711",
    "TW3714",
    "TW3715",
    "TW4749",
    "TW4919",
    "TW4958",
    "TW4967",
    "TW4971",
    "TW4977",
    "TW4979",
    "TW4989",
    "TW4991",
    "TW5269",
    "TW5274",
    "TW5289",
    "TW5347",
    "TW5351",
    "TW5439",
    "TW5483",
    "TW5536",
    "TW6139",
    "TW6147",
    "TW6187",
    "TW6213",
    "TW6223",
    "TW6239",
    "TW6257",
    "TW6271",
    "TW6274",
    "TW6282",
    "TW6285",
    "TW6290",
    "TW6415",
    "TW6442",
    "TW6443",
    "TW6446",
    "TW6488",
    "TW6505",
    "TW6510",
    "TW6515",
    "TW6531",
    "TW6669",
    "TW6683",
    "TW6770",
    "TW6781",
    "TW6789",
    "TW6805",
    "TW6919",
    "TW7769",
    "TW8021",
    "TW8028",
    "TW8039",
    "TW8046",
    "TW8096",
    "TW8110",
    "TW8112",
    "TW8150",
    "TW8210",
    "TW8299",
    "TW8358",
    "TW8996"
  ],
  "symbols_failed": {
    "TW1301": [
      {
        "ticker": "1301.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1301.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1303": [
      {
        "ticker": "1303.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1303.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1326": [
      {
        "ticker": "1326.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1326.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1519": [
      {
        "ticker": "1519.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1519.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1560": [
      {
        "ticker": "1560.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1560.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1590": [
      {
        "ticker": "1590.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1590.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1605": [
      {
        "ticker": "1605.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1605.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1711": [
      {
        "ticker": "1711.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1711.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1717": [
      {
        "ticker": "1717.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1717.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1785": [
      {
        "ticker": "1785.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1785.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1802": [
      {
        "ticker": "1802.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1802.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW1815": [
      {
        "ticker": "1815.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "1815.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2049": [
      {
        "ticker": "2049.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2049.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2059": [
      {
        "ticker": "2059.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2059.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2301": [
      {
        "ticker": "2301.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2301.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2303": [
      {
        "ticker": "2303.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2303.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2308": [
      {
        "ticker": "2308.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2308.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2313": [
      {
        "ticker": "2313.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2313.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2317": [
      {
        "ticker": "2317.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2317.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2324": [
      {
        "ticker": "2324.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2324.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2327": [
      {
        "ticker": "2327.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2327.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2330": [
      {
        "ticker": "2330.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2330.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2337": [
      {
        "ticker": "2337.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2337.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2344": [
      {
        "ticker": "2344.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2344.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2345": [
      {
        "ticker": "2345.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2345.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2357": [
      {
        "ticker": "2357.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2357.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2360": [
      {
        "ticker": "2360.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2360.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2367": [
      {
        "ticker": "2367.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2367.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2368": [
      {
        "ticker": "2368.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2368.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2376": [
      {
        "ticker": "2376.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2376.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2379": [
      {
        "ticker": "2379.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2379.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2382": [
      {
        "ticker": "2382.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2382.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2383": [
      {
        "ticker": "2383.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2383.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2404": [
      {
        "ticker": "2404.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2404.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2408": [
      {
        "ticker": "2408.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2408.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2409": [
      {
        "ticker": "2409.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2409.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2412": [
      {
        "ticker": "2412.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2412.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2449": [
      {
        "ticker": "2449.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2449.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2451": [
      {
        "ticker": "2451.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2451.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2454": [
      {
        "ticker": "2454.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2454.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2455": [
      {
        "ticker": "2455.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2455.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2467": [
      {
        "ticker": "2467.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2467.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2481": [
      {
        "ticker": "2481.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2481.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2485": [
      {
        "ticker": "2485.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2485.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2486": [
      {
        "ticker": "2486.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2486.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2489": [
      {
        "ticker": "2489.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2489.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2492": [
      {
        "ticker": "2492.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2492.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2603": [
      {
        "ticker": "2603.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2603.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2609": [
      {
        "ticker": "2609.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2609.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2881": [
      {
        "ticker": "2881.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2881.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2882": [
      {
        "ticker": "2882.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2882.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2887": [
      {
        "ticker": "2887.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2887.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW2891": [
      {
        "ticker": "2891.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "2891.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3006": [
      {
        "ticker": "3006.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3006.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3008": [
      {
        "ticker": "3008.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3008.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3017": [
      {
        "ticker": "3017.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3017.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3030": [
      {
        "ticker": "3030.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3030.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3034": [
      {
        "ticker": "3034.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3034.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3036": [
      {
        "ticker": "3036.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3036.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3037": [
      {
        "ticker": "3037.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3037.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3044": [
      {
        "ticker": "3044.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3044.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3081": [
      {
        "ticker": "3081.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3081.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3105": [
      {
        "ticker": "3105.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3105.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3131": [
      {
        "ticker": "3131.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3131.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3163": [
      {
        "ticker": "3163.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3163.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3167": [
      {
        "ticker": "3167.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3167.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3189": [
      {
        "ticker": "3189.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3189.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3211": [
      {
        "ticker": "3211.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3211.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3231": [
      {
        "ticker": "3231.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3231.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3260": [
      {
        "ticker": "3260.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3260.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3264": [
      {
        "ticker": "3264.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3264.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3293": [
      {
        "ticker": "3293.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3293.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3324": [
      {
        "ticker": "3324.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3324.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3363": [
      {
        "ticker": "3363.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3363.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3374": [
      {
        "ticker": "3374.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3374.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3376": [
      {
        "ticker": "3376.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3376.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3443": [
      {
        "ticker": "3443.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3443.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3450": [
      {
        "ticker": "3450.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3450.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3481": [
      {
        "ticker": "3481.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3481.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3491": [
      {
        "ticker": "3491.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3491.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3529": [
      {
        "ticker": "3529.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3529.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3533": [
      {
        "ticker": "3533.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3533.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3563": [
      {
        "ticker": "3563.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3563.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3583": [
      {
        "ticker": "3583.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3583.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3653": [
      {
        "ticker": "3653.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3653.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3661": [
      {
        "ticker": "3661.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3661.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3665": [
      {
        "ticker": "3665.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3665.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3693": [
      {
        "ticker": "3693.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3693.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3702": [
      {
        "ticker": "3702.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3702.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3711": [
      {
        "ticker": "3711.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3711.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3714": [
      {
        "ticker": "3714.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3714.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW3715": [
      {
        "ticker": "3715.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "3715.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4749": [
      {
        "ticker": "4749.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4749.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4919": [
      {
        "ticker": "4919.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4919.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4958": [
      {
        "ticker": "4958.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4958.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4967": [
      {
        "ticker": "4967.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4967.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4971": [
      {
        "ticker": "4971.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4971.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4977": [
      {
        "ticker": "4977.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4977.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4979": [
      {
        "ticker": "4979.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4979.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4989": [
      {
        "ticker": "4989.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4989.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW4991": [
      {
        "ticker": "4991.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "4991.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5269": [
      {
        "ticker": "5269.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5269.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5274": [
      {
        "ticker": "5274.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5274.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5289": [
      {
        "ticker": "5289.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5289.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5347": [
      {
        "ticker": "5347.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5347.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5351": [
      {
        "ticker": "5351.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5351.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5439": [
      {
        "ticker": "5439.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5439.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5483": [
      {
        "ticker": "5483.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5483.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW5536": [
      {
        "ticker": "5536.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "5536.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6139": [
      {
        "ticker": "6139.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6139.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6147": [
      {
        "ticker": "6147.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6147.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6187": [
      {
        "ticker": "6187.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6187.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6213": [
      {
        "ticker": "6213.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6213.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6223": [
      {
        "ticker": "6223.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6223.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6239": [
      {
        "ticker": "6239.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6239.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6257": [
      {
        "ticker": "6257.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6257.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6271": [
      {
        "ticker": "6271.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6271.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6274": [
      {
        "ticker": "6274.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6274.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6282": [
      {
        "ticker": "6282.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6282.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6285": [
      {
        "ticker": "6285.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6285.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6290": [
      {
        "ticker": "6290.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6290.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6415": [
      {
        "ticker": "6415.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6415.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6442": [
      {
        "ticker": "6442.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6442.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6443": [
      {
        "ticker": "6443.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6443.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6446": [
      {
        "ticker": "6446.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6446.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6488": [
      {
        "ticker": "6488.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6488.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6505": [
      {
        "ticker": "6505.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6505.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6510": [
      {
        "ticker": "6510.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6510.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6515": [
      {
        "ticker": "6515.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6515.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6531": [
      {
        "ticker": "6531.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6531.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6669": [
      {
        "ticker": "6669.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6669.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6683": [
      {
        "ticker": "6683.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6683.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6770": [
      {
        "ticker": "6770.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6770.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6781": [
      {
        "ticker": "6781.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6781.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6789": [
      {
        "ticker": "6789.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6789.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6805": [
      {
        "ticker": "6805.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6805.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW6919": [
      {
        "ticker": "6919.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "6919.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW7769": [
      {
        "ticker": "7769.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "7769.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8021": [
      {
        "ticker": "8021.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8021.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8028": [
      {
        "ticker": "8028.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8028.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8039": [
      {
        "ticker": "8039.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8039.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8046": [
      {
        "ticker": "8046.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8046.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8096": [
      {
        "ticker": "8096.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8096.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8110": [
      {
        "ticker": "8110.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8110.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8112": [
      {
        "ticker": "8112.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8112.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8150": [
      {
        "ticker": "8150.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8150.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8210": [
      {
        "ticker": "8210.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8210.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8299": [
      {
        "ticker": "8299.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8299.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8358": [
      {
        "ticker": "8358.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8358.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ],
    "TW8996": [
      {
        "ticker": "8996.TW",
        "status": 403,
        "error": "http_status:403:"
      },
      {
        "ticker": "8996.TWO",
        "status": 403,
        "error": "http_status:403:"
      }
    ]
  },
  "rows_written": 0,
  "suffix_used": {},
  "http_status_counts": {
    "403": 300
  },
  "per_symbol_sample": [],
  "adjustment": "yahoo_adjusted_ohlc_factor_adjclose_over_close"
}
```

## Normalized Validation

```json
{
  "status": "fail",
  "errors": [
    "missing_files"
  ],
  "data_dir": "/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy/candidate_normalized",
  "symbols_expected": 150,
  "files_found": 0,
  "missing_count": 150,
  "empty_count": 0,
  "issue_symbol_count": 0,
  "symbols_with_asof": 0,
  "missing_asof_count": 0,
  "date_max_min": null,
  "date_max_max": null,
  "total_rows": 0,
  "missing_symbols": [
    "TW1301",
    "TW1303",
    "TW1326",
    "TW1519",
    "TW1560",
    "TW1590",
    "TW1605",
    "TW1711",
    "TW1717",
    "TW1785",
    "TW1802",
    "TW1815",
    "TW2049",
    "TW2059",
    "TW2301",
    "TW2303",
    "TW2308",
    "TW2313",
    "TW2317",
    "TW2324",
    "TW2327",
    "TW2330",
    "TW2337",
    "TW2344",
    "TW2345",
    "TW2357",
    "TW2360",
    "TW2367",
    "TW2368",
    "TW2376",
    "TW2379",
    "TW2382",
    "TW2383",
    "TW2404",
    "TW2408",
    "TW2409",
    "TW2412",
    "TW2449",
    "TW2451",
    "TW2454",
    "TW2455",
    "TW2467",
    "TW2481",
    "TW2485",
    "TW2486",
    "TW2489",
    "TW2492",
    "TW2603",
    "TW2609",
    "TW2881",
    "TW2882",
    "TW2887",
    "TW2891",
    "TW3006",
    "TW3008",
    "TW3017",
    "TW3030",
    "TW3034",
    "TW3036",
    "TW3037",
    "TW3044",
    "TW3081",
    "TW3105",
    "TW3131",
    "TW3163",
    "TW3167",
    "TW3189",
    "TW3211",
    "TW3231",
    "TW3260",
    "TW3264",
    "TW3293",
    "TW3324",
    "TW3363",
    "TW3374",
    "TW3376",
    "TW3443",
    "TW3450",
    "TW3481",
    "TW3491",
    "TW3529",
    "TW3533",
    "TW3563",
    "TW3583",
    "TW3653",
    "TW3661",
    "TW3665",
    "TW3693",
    "TW3702",
    "TW3711",
    "TW3714",
    "TW3715",
    "TW4749",
    "TW4919",
    "TW4958",
    "TW4967",
    "TW4971",
    "TW4977",
    "TW4979",
    "TW4989",
    "TW4991",
    "TW5269",
    "TW5274",
    "TW5289",
    "TW5347",
    "TW5351",
    "TW5439",
    "TW5483",
    "TW5536",
    "TW6139",
    "TW6147",
    "TW6187",
    "TW6213",
    "TW6223",
    "TW6239",
    "TW6257",
    "TW6271",
    "TW6274",
    "TW6282",
    "TW6285",
    "TW6290",
    "TW6415",
    "TW6442",
    "TW6443",
    "TW6446",
    "TW6488",
    "TW6505",
    "TW6510",
    "TW6515",
    "TW6531",
    "TW6669",
    "TW6683",
    "TW6770",
    "TW6781",
    "TW6789",
    "TW6805",
    "TW6919",
    "TW7769",
    "TW8021",
    "TW8028",
    "TW8039",
    "TW8046",
    "TW8096",
    "TW8110",
    "TW8112",
    "TW8150",
    "TW8210",
    "TW8299",
    "TW8358",
    "TW8996"
  ],
  "empty_symbols": [],
  "missing_asof_symbols": [],
  "issues_sample": {},
  "per_symbol_sample": []
}
```

## Provider Validation

```json
{
  "status": "not_run"
}
```

## Model Smoke

```json
{
  "status": "not_run"
}
```

## Explicit Non-Actions

- No FinMind fallback or mixed-provider fill was used.
- No formal normalized directory was overwritten.
- No formal qlib provider was overwritten.
- No latest_signal.json was updated.
- No paper/live trading, broker connection, orders, target positions, retraining, tuning, recorder switch, or universe expansion was performed.
