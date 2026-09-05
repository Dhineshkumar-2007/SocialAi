from functools import lru_cache
from PIL import Image
from config import Config
from ai.embeddings import generate_embedding


@lru_cache(maxsize=1)
def get_vision():
    if not Config.AI_ENABLED:
        return None

    from transformers import BlipProcessor, BlipForConditionalGeneration

    processor = BlipProcessor.from_pretrained(Config.VISION_MODEL)
    model = BlipForConditionalGeneration.from_pretrained(
        Config.VISION_MODEL
    )

    return processor, model


def cosine_similarity(a, b):
    if not a or not b:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))

    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def analyze_image(path, problem_text):

    vision = get_vision()

    if vision is None:
        return {
            "caption": "Vision model disabled",
            "supports_report": False,
            "confidence": 0.0
        }

    processor, model = vision

    try:
        image = Image.open(path).convert("RGB")

        # Generate image caption
        inputs = processor(
            images=image,
            return_tensors="pt"
        )

        output = model.generate(
            **inputs,
            max_new_tokens=40
        )

        caption = processor.decode(
            output[0],
            skip_special_tokens=True
        )

        # ------------------------------------------------
        # Compare problem text and image caption
        # ------------------------------------------------

        problem_embedding = generate_embedding(problem_text)
        image_embedding = generate_embedding(caption)

        similarity = cosine_similarity(
            problem_embedding,
            image_embedding
        )

        # Convert cosine similarity into evidence score
        #
        # Very low similarity  -> irrelevant
        # Medium similarity    -> uncertain
        # High similarity      -> supporting evidence

                # ---------------------------------------------
        # Evidence decision
        # ---------------------------------------------

        if similarity < 0.50:
            confidence = 0.0
            supports_report = False
            evidence_status = "irrelevant"

        elif similarity < 0.65:
            confidence = 0.30
            supports_report = False
            evidence_status = "uncertain"

        else:
            # Supporting evidence
            confidence = 0.80 + (
                (similarity - 0.65) / 0.35
            ) * 0.15

            confidence = min(confidence, 0.95)

            supports_report = True
            evidence_status = "supporting"
        print("================================")
        print("PROBLEM:", problem_text)
        print("IMAGE CAPTION:", caption)
        print("SIMILARITY:", similarity)
        print("================================")
        return {
            "caption": caption,
            "supports_report": supports_report,
            "confidence": round(float(confidence), 3),
            "similarity": round(float(similarity), 3),
            "evidence_status": evidence_status
        }
    except Exception as e:

        return {
            "caption": f"Unable to analyze image: {str(e)}",
            "supports_report": False,
            "confidence": 0.0,
            "similarity": 0.0,
            "evidence_status": "error"
        }
    