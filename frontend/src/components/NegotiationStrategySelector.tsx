import type { NegotiationStrategy } from "../api/types";

type Props = {
  value: NegotiationStrategy;
  onChange: (strategy: NegotiationStrategy) => void;
};

export function NegotiationStrategySelector({ value, onChange }: Props) {
  return (
    <div className="strategy-selector">
      <label className="strategy-selector__label">Negotiation strategy</label>
      <div className="strategy-options">
        <button
          type="button"
          className={`strategy-option${value === "conceder" ? " strategy-option--active" : ""}`}
          onClick={() => onChange("conceder")}
        >
          <span className="strategy-option__title">🤝 Cooperative (Conceder)</span>
          <span className="strategy-option__desc">
            Concede early — prioritise quick deal over max price
          </span>
        </button>
        <button
          type="button"
          className={`strategy-option${value === "boulware" ? " strategy-option--active" : ""}`}
          onClick={() => onChange("boulware")}
        >
          <span className="strategy-option__title">💪 Aggressive (Boulware)</span>
          <span className="strategy-option__desc">
            Hold firm until final round — maximise price, risk no-deal
          </span>
        </button>
      </div>
    </div>
  );
}
