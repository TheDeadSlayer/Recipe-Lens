from app.services.transcript.base import TranscriptProvider, TranscriptUnavailableError

FAIL_URL = "https://example.com/fail"

_MOCK_TRANSCRIPT = """
Welcome back to the channel. Today we're making a classic lemon herb roasted chicken.
You'll need one whole chicken, about 1.5 kilograms, two lemons, four cloves of garlic,
a handful of fresh rosemary and thyme, two tablespoons of olive oil, salt, and black pepper.

First, preheat your oven to 200 degrees Celsius. While the oven heats up, pat the chicken
dry with paper towels — this is the key to crispy skin. Zest one lemon and juice both of them.
Crush the garlic cloves with the flat of your knife.

In a small bowl, mix the olive oil, lemon zest, lemon juice, garlic, rosemary, and thyme.
Season generously with salt and pepper. Rub this mixture all over the chicken, making sure
to get under the skin on the breast.

Place the chicken in a roasting tin breast-side up. Roast for 20 minutes per 500 grams,
plus an extra 20 minutes — so about 80 minutes total for a 1.5 kg bird.

Let it rest for 10 minutes before carving. Each serving is roughly 350 calories, 42 grams
of protein, 2 grams of carbs, and 18 grams of fat. Enjoy!
""".strip()


class MockTranscriptProvider(TranscriptProvider):
    """Returns a realistic hardcoded cooking transcript. No external calls."""

    def fetch(self, url: str) -> str:
        if url == FAIL_URL:
            raise TranscriptUnavailableError(f"Simulated failure for URL: {url}")
        return _MOCK_TRANSCRIPT
