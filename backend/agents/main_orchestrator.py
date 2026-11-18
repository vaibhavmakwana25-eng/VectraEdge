from typing import Dict, List
from config import MIN_CONFIDENCE_SCORE, REQUIRE_POSITIVE_NET_PROFIT
from math_engine import calculate_one_lot_pnl, calculate_profit_percent, verify_multi_leg_strategy
from agents.indicator_agent import run_indicator_agent
from agents.volume_agent import run_volume_agent
from agents.fno_strategy_agent import run_fno_strategy_agent
from agents.sentiment_news_agent import run_sentiment_news_agent
from agents.backtest_agent import run_backtest_agent


class MainAgentOrchestrator:
    def evaluate_candidate(self, raw_setup: Dict) -> Dict | None:
        agent_outputs = {
            "indicator": run_indicator_agent(raw_setup),
            "volume": run_volume_agent(raw_setup),
            "fno_strategy": run_fno_strategy_agent(raw_setup),
            "sentiment_news": run_sentiment_news_agent(raw_setup),
            "backtest_2008": run_backtest_agent(raw_setup),
        }

        for report in agent_outputs.values():
            if not report or not report.get("ok"):
                return None

        weights = {
            "indicator": 0.25,
            "volume": 0.20,
            "fno_strategy": 0.20,
            "sentiment_news": 0.15,
            "backtest_2008": 0.20,
        }
        total_score = sum(float(agent_outputs[k].get("score", 0.0)) * w for k, w in weights.items())
        if total_score < MIN_CONFIDENCE_SCORE:
            return None

        entry = float(raw_setup["entry"])
        target = float(raw_setup["target"])
        min_target = float(raw_setup["min_target"])
        sl = float(raw_setup["sl"])
        min_sl = float(raw_setup["min_sl"])
        lot_size = int(raw_setup["lot_size"])
        side = raw_setup.get("side", "BUY")
        is_fno = bool(raw_setup.get("is_fno", True))

        profit_pct = calculate_profit_percent(entry=entry, target=target, side=side)
        lot_pnl = calculate_one_lot_pnl(
            entry=entry,
            target=target,
            min_target=min_target,
            sl=sl,
            min_sl=min_sl,
            lot_size=lot_size,
            side=side,
            is_fno=is_fno,
        )

        if REQUIRE_POSITIVE_NET_PROFIT and lot_pnl.max_profit <= 0:
            return None

        multi_leg_check = verify_multi_leg_strategy(raw_setup.get("multi_leg", []))

        return {
            "symbol": raw_setup["symbol"],
            "segment": raw_setup["segment"],
            "ltp": float(raw_setup["ltp"]),
            "profit_pct": profit_pct,
            "entry": entry,
            "sl": sl,
            "target": target,
            "lot_pnl": {
                "lot_size": lot_pnl.lot_size,
                "max_profit": lot_pnl.max_profit,
                "min_profit": lot_pnl.min_profit,
                "max_loss": lot_pnl.max_loss,
                "min_loss": lot_pnl.min_loss,
                "charges_est": lot_pnl.net_charges_est,
            },
            "multi_leg": multi_leg_check if multi_leg_check.get("valid") else None,
            "confidence_score": round(total_score, 2),
        }

    def scan_all(self, candidates: List[Dict]) -> List[Dict]:
        results = []
        for item in candidates:
            try:
                sig = self.evaluate_candidate(item)
                if sig:
                    results.append(sig)
            except Exception:
                continue
        return results
