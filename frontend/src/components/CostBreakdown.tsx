import type { Costs } from "../api";
import { paiseToRupees } from "../utils/format";

export function CostBreakdown({ costs, taxBasis = "before tax" }: { costs: Costs; taxBasis?: string }) {
  return (
    <table className="cost-table">
      <tbody>
        <tr>
          <td>Material</td>
          <td className="cost-table__num">₹{paiseToRupees(costs.material_paise)}</td>
        </tr>
        <tr>
          <td>Freight</td>
          <td className="cost-table__num">₹{paiseToRupees(costs.freight_paise)}</td>
        </tr>
        <tr className="cost-table__total">
          <td>Buyer pays</td>
          <td className="cost-table__num">₹{paiseToRupees(costs.buyer_total_paise)}</td>
        </tr>
        <tr>
          <td>Seller receives</td>
          <td className="cost-table__num">₹{paiseToRupees(costs.seller_receives_paise)}</td>
        </tr>
      </tbody>
      <caption>Amounts shown {taxBasis}.</caption>
    </table>
  );
}
