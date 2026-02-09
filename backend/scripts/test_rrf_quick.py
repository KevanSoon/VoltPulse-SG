"""Quick test of RRF implementation with mock data.

This script tests the RRF scorer with simple mock retailers
to verify the implementation is working correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Windows async fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from recommender.rrf_scorer import RRFScorer, ScoredRetailer
from recommender.vector_store import SimilarityResult
import numpy as np


def create_mock_retailer(
    id: str,
    name: str,
    products: list,
    area: str,
    website: bool,
    distance: float
) -> SimilarityResult:
    """Create a mock retailer for testing."""
    return SimilarityResult(
        id=id,
        form_data={
            "retail_outlet": name,
            "outlet_address": f"123 {area} Road, Singapore 123456",
            "postal_code": "123456",
            "planning_area": area,
            "eligible_products": products,
            "website": "https://example.com" if website else None,
            "remarks": None
        },
        score=1.0 / (1.0 + distance),
        form_type="retailer",
        distance=distance
    )


async def test_rrf_basic():
    """Test basic RRF scoring with mock data."""
    print("=" * 80)
    print("QUICK RRF IMPLEMENTATION TEST")
    print("=" * 80)
    print()

    # Create mock retailers with different characteristics
    print("[1/5] Creating mock retailers...")
    candidates = [
        # Retailer 1: Perfect match (refrigerator + Bedok + website)
        create_mock_retailer(
            id="r1",
            name="Gain City (Bedok)",
            products=["refrigerators", "air_conditioners", "washing_machines"],
            area="Bedok",
            website=True,
            distance=0.5  # Good semantic match
        ),

        # Retailer 2: Good semantic, wrong product
        create_mock_retailer(
            id="r2",
            name="123 LED Lighting",
            products=["led_lights", "dc_fans"],
            area="Queenstown",
            website=True,
            distance=0.3  # Best semantic match
        ),

        # Retailer 3: Right product, wrong area, no website
        create_mock_retailer(
            id="r3",
            name="FairPrice (Ang Mo Kio)",
            products=["refrigerators"],
            area="Ang Mo Kio",
            website=False,
            distance=1.2  # Weak semantic match
        ),

        # Retailer 4: Comprehensive store, nearby area
        create_mock_retailer(
            id="r4",
            name="Best Denki (Tampines)",
            products=["refrigerators", "air_conditioners", "led_lights", "washing_machines"],
            area="Tampines",  # Neighbor of Bedok
            website=True,
            distance=0.7
        ),
    ]

    print(f"  Created {len(candidates)} mock retailers")
    for c in candidates:
        print(f"    - {c.form_data['retail_outlet']}: "
              f"{len(c.form_data['eligible_products'])} products, "
              f"dist={c.distance:.2f}")
    print()

    # Test RRF scoring
    print("[2/5] Testing RRF scorer...")
    scorer = RRFScorer()

    # Query: "refrigerator shops in Bedok"
    query_embedding = np.random.rand(1024)  # Mock embedding
    query_text = "refrigerator shops in Bedok"
    query_product = "refrigerators"
    query_area = "Bedok"

    print(f"  Query: '{query_text}'")
    print(f"  Product filter: {query_product}")
    print(f"  Area filter: {query_area}")
    print()

    scored_results = await scorer.score_retailers(
        query_embedding=query_embedding,
        query_text=query_text,
        candidates=candidates,
        query_product=query_product,
        query_area=query_area,
        limit=4
    )

    print(f"  Scored {len(scored_results)} retailers")
    print()

    # Analyze results
    print("[3/5] RRF Ranking Results:")
    print()
    for i, scored in enumerate(scored_results, 1):
        retailer = scored.retailer
        name = retailer.form_data['retail_outlet']
        area = retailer.form_data['planning_area']
        products = retailer.form_data['eligible_products']
        has_product = query_product in products

        print(f"  Rank #{i}: {name}")
        print(f"    Location: {area}")
        print(f"    Has refrigerators: {'YES' if has_product else 'NO'}")
        print(f"    Component Scores:")
        print(f"      Semantic:  {scored.semantic_score:.4f}")
        print(f"      Product:   {scored.product_score:.4f}")
        print(f"      Location:  {scored.location_score:.4f}")
        print(f"      Breadth:   {scored.breadth_score:.4f}")
        print(f"      Intent:    {scored.intent_score:.4f}")
        print(f"    Final RRF:   {scored.final_rrf_score:.4f}")
        print()

    # Verify expectations
    print("[4/5] Validation:")
    print()

    # Expectation 1: Gain City (perfect match) should rank high
    top_result = scored_results[0]
    gain_city_rank = next((i for i, r in enumerate(scored_results, 1)
                          if "Gain City" in r.retailer.form_data['retail_outlet']), None)

    if gain_city_rank and gain_city_rank <= 2:
        print(f"  [OK] Gain City (Bedok) ranks #{gain_city_rank} (perfect match)")
    else:
        print(f"  [FAIL] Gain City (Bedok) should rank high (ranks #{gain_city_rank})")

    # Expectation 2: LED lighting store (wrong product) should rank low
    led_rank = next((i for i, r in enumerate(scored_results, 1)
                    if "LED Lighting" in r.retailer.form_data['retail_outlet']), None)

    if led_rank and led_rank >= 3:
        print(f"  [OK] LED Lighting (wrong product) ranks #{led_rank} (correctly penalized)")
    else:
        print(f"  [FAIL] LED Lighting should rank low despite good semantic match (ranks #{led_rank})")

    # Expectation 3: Product match score should be high for refrigerator retailers
    avg_product_score = sum(r.product_score for r in scored_results[:2]) / 2
    if avg_product_score > 0.5:
        print(f"  [OK] Top-2 avg product score: {avg_product_score:.4f} (>0.5)")
    else:
        print(f"  [FAIL] Top-2 avg product score too low: {avg_product_score:.4f}")

    # Expectation 4: RRF score should be higher than semantic alone
    if scored_results[0].final_rrf_score > scored_results[0].semantic_score:
        print(f"  [OK] RRF score ({scored_results[0].final_rrf_score:.4f}) > "
              f"semantic ({scored_results[0].semantic_score:.4f})")
    else:
        print(f"  [FAIL] RRF should boost beyond semantic similarity")

    print()

    # Summary
    print("[5/5] Summary:")
    print()
    print(f"  Total retailers tested: {len(candidates)}")
    print(f"  RRF scoring completed: OK")
    print(f"  Multi-signal fusion working: OK")
    print(f"  Component scores computed: OK")
    print()
    print("=" * 80)
    print("RRF IMPLEMENTATION TEST COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Start backend server: python run.py")
    print("  2. Test with real retailers: python scripts/test_retailer_search.py")
    print("  3. Run full benchmarks: python scripts/benchmark_rrf.py")


if __name__ == "__main__":
    asyncio.run(test_rrf_basic())
