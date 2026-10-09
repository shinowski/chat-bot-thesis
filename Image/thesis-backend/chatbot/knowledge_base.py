CONDITION_INFO = {
    "atopic_dermatitis": {
        "display_name": "Atopic Dermatitis",
        "description": (
            "A chronic inflammatory skin condition that commonly causes "
            "dryness, itching, redness, and irritated patches. It often "
            "appears on areas such as the face, hands, elbows, and knees "
            "and may flare periodically."
        ),
        "summary": (
            "The image was classified as Atopic Dermatitis based on "
            "overall visual similarity to atopic dermatitis images in "
            "the model's training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of atopic dermatitis it was trained on. This reflects "
            "overall color, texture, and structural similarity across "
            "the image — the model does not identify or name specific "
            "clinical features, only statistical patterns."
        ),
        "recommendations": (
            "Consider using fragrance-free moisturizers, avoiding known "
            "triggers such as harsh soaps or extreme temperatures, and "
            "scheduling a visit with a dermatologist to confirm the "
            "diagnosis and discuss treatment options."
        ),
        # --- chatbot-only fields below ---
        "symptoms": (
            "Dry, intensely itchy skin with red, inflamed patches. Chronic "
            "and relapsing, often starting in childhood."
        ),
        "triggers": (
            "Dry weather, harsh soaps/detergents, allergens (dust mites, "
            "pet dander), sweating, stress, and certain fabrics like wool."
        ),
        "appearance": (
            "Red, scaly, sometimes weepy or thickened (lichenified) "
            "patches, typically in skin folds -- elbow creases, behind "
            "knees, neck, wrists."
        ),
        "seek_help": (
            "See a doctor if skin shows signs of infection (oozing, "
            "crusting, fever), sleep is disrupted by itching, or symptoms "
            "don't improve with basic skincare."
        ),
        "sources": ["TODO: add references"],
    },

    "contact_dermatitis": {
        "display_name": "Contact Dermatitis",
        "description": (
            "An inflammatory skin reaction that can occur after contact "
            "with an irritating substance or an allergen. It may cause "
            "redness, itching, swelling, dryness, or a rash in the area "
            "that was exposed."
        ),
        "summary": (
            "The image was classified as Contact Dermatitis based on "
            "overall visual similarity to contact dermatitis images in "
            "the model's training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of contact dermatitis it was trained on. This reflects "
            "overall color, texture, and structural similarity, the "
            "model does not identify or name specific clinical features, "
            "only statistical patterns."
        ),
        "recommendations": (
            "Try to identify and avoid the substance that may have "
            "triggered the reaction, keep the area clean and moisturized, "
            "and see a dermatologist if the irritation persists or worsens."
        ),
        "symptoms": (
            "Red, itchy, sometimes blistered or swollen skin appearing "
            "where it touched an irritant or allergen."
        ),
        "triggers": (
            "Direct contact with irritants (soaps, chemicals, detergents) "
            "or allergens (nickel, fragrances, certain plants like poison "
            "ivy, latex)."
        ),
        "appearance": (
            "Redness and irritation confined to the area of contact, "
            "sometimes with clear borders matching the shape of the "
            "trigger (e.g. a watch strap, jewelry)."
        ),
        "seek_help": (
            "See a doctor if the reaction is widespread, involves the "
            "face/genitals, blisters heavily, or doesn't improve after "
            "removing the suspected trigger."
        ),
        "sources": ["TODO: add references"],
    },

    "lichen_planus": {
        "display_name": "Lichen Planus",
        "description": (
            "An inflammatory skin condition that can cause itchy, "
            "purplish, flat-topped bumps or patches. It commonly affects "
            "the wrists, ankles, lower back, and other areas of the skin."
        ),
        "summary": (
            "The image was classified as Lichen Planus based on overall "
            "visual similarity to lichen planus images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of lichen planus it was trained on. This reflects overall "
            "color, texture, and structural similarity, the model does "
            "not identify or name specific clinical features, only "
            "statistical patterns."
        ),
        "recommendations": (
            "Avoid scratching the affected area, note whether the "
            "patches spread or change over time, and consult a "
            "dermatologist for confirmation and treatment options."
        ),
        "symptoms": (
            "Itchy, flat-topped, purplish (violaceous) bumps, often with "
            "fine white lines on the surface (Wickham striae). Can also "
            "affect the mouth as white lacy patches."
        ),
        "triggers": (
            "Sometimes linked to hepatitis C infection, certain "
            "medications, or contact allergens; often no clear trigger "
            "is found."
        ),
        "appearance": (
            "Small, polygonal, flat-topped papules with a violet hue, "
            "commonly on wrists, forearms, ankles, or lower back."
        ),
        "seek_help": (
            "See a doctor if lesions spread rapidly, involve the "
            "mouth/genitals, or are very itchy and not improving with "
            "basic care."
        ),
        "sources": ["TODO: add references"],
    },

    "psoriasis": {
        "display_name": "Psoriasis",
        "description": (
            "A chronic inflammatory skin condition that causes areas of "
            "the skin to become red, thickened, and covered with "
            "silvery-white scales. It commonly affects the elbows, knees, "
            "scalp, and other areas, although it can occur elsewhere."
        ),
        "summary": (
            "The image was classified as Psoriasis based on overall "
            "visual similarity to psoriasis images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of psoriasis it was trained on. This reflects overall "
            "color, texture, and structural similarity, the model does "
            "not identify or name specific clinical features (such as "
            "plaque type or scale texture), only statistical patterns "
            "learned from the training images available to it."
        ),
        "recommendations": (
            "Moisturize regularly, avoid known triggers such as stress "
            "and skin trauma, and schedule a visit with a dermatologist "
            "to confirm the diagnosis and discuss treatment options."
        ),
        "symptoms": (
            "Raised, well-demarcated red or pink plaques covered with "
            "silvery-white scale. Commonly itchy or sore, sometimes "
            "cracking or bleeding. Frequently appears on elbows, knees, "
            "scalp, and lower back."
        ),
        "triggers": (
            "Stress, skin injury (Koebner phenomenon), infections (e.g. "
            "strep throat), cold/dry weather, certain medications, and "
            "smoking or heavy alcohol use."
        ),
        "appearance": (
            "Sharply bordered plaques with thick silvery scale, often "
            "symmetric on both sides of the body."
        ),
        "seek_help": (
            "See a dermatologist if plaques cover a large body area, are "
            "painful, show signs of infection, or are affecting joints "
            "(possible psoriatic arthritis)."
        ),
        "sources": ["TODO: add references"],
    },

    "rosacea": {
        "display_name": "Rosacea",
        "description": (
            "A chronic skin condition that commonly affects the face and "
            "may cause persistent redness, flushing, visible blood vessels, "
            "and sometimes small red bumps or pustules. Symptoms may become "
            "more noticeable after certain triggers."
        ),
        "summary": (
            "The image was classified as Rosacea based on overall "
            "visual similarity to rosacea images in the model's "
            "training data."
        ),
        "why": (
            "The model's learned patterns most closely matched examples "
            "of rosacea it was trained on. This reflects overall color, "
            "texture, and structural similarity, the model does not "
            "identify or name specific clinical features, only "
            "statistical patterns."
        ),
        "recommendations": (
            "Identify and avoid common triggers such as sun exposure, "
            "spicy food, or alcohol, use gentle skincare products, and "
            "consult a dermatologist for confirmation and treatment "
            "options."
        ),
        "symptoms": (
            "Persistent facial redness, visible small blood vessels, and "
            "sometimes small red bumps or pus-filled pimples. Skin may "
            "feel warm or sting."
        ),
        "triggers": (
            "Sun exposure, spicy food, alcohol, hot drinks, temperature "
            "extremes, stress, and certain skincare products."
        ),
        "appearance": (
            "Central facial redness (cheeks, nose, forehead, chin), "
            "sometimes with visible tiny blood vessels or acne-like "
            "bumps, usually without blackheads."
        ),
        "seek_help": (
            "See a dermatologist if redness is persistent/worsening, "
            "eyes are affected (gritty/red eyes), or the nose becomes "
            "thickened."
        ),
        "sources": ["TODO: add references"],
    },

    "normal_skin": {
        "display_name": "No Supported Condition Detected",
        "description": (
            "This tool screens close-up photos for five specific skin "
            "conditions, and none of them was detected in this image. "
            "This is not a clearance: it does not confirm that the skin "
            "is healthy, and it cannot rule out other conditions. If you "
            "have a spot or symptom that concerns you, consult a "
            "qualified healthcare professional."
        ),
        "summary": (
            "The image's overall visual pattern did not match any of the "
            "five conditions this tool screens for, and was closest to "
            "the unaffected skin images in the model's training data."
        ),
        "why": (
            "The model's learned patterns did not match any of the five "
            "supported conditions. This is a pattern match against its "
            "training images, not a clinical clearance, and the model "
            "can miss small or distant lesions and conditions outside "
            "its scope."
        ),
        "recommendations": (
            "If a spot, bump, or area of skin concerns you, consult a "
            "dermatologist directly, whatever this result says. For best "
            "results, retake the photo as a close-up in good light."
        ),
        "symptoms": (
            "None of the supported conditions was matched. This does not "
            "rule out other skin conditions."
        ),
        "triggers": "Not applicable.",
        "appearance": (
            "The visible area did not resemble the supported conditions. "
            "A photo cannot confirm that skin is healthy."
        ),
        "seek_help": (
            "If you have a changing, painful, itchy, bleeding or "
            "persistent spot or rash, get it checked even if this tool "
            "found nothing, since a photo can miss early, subtle, or "
            "out-of-scope conditions."
        ),
        "sources": ["TODO: add references"],
    },
}

"""
App-level FAQ content -- separate from CONDITION_INFO (which is medical
content about the 6 skin conditions). This covers meta-questions about
Flamma itself: how it works, what to upload, how much to trust a result,
and privacy. These are the same 4 topics the old hardcoded getReply()
function in the frontend used to answer.
"""

APP_FAQ = {
       "how_it_works": (
        "Flamma analyzes an uploaded close-up skin image using a CNN "
        "model trained to recognize visual patterns associated with five "
        "conditions: Psoriasis, Lichen Planus, Rosacea, Atopic Dermatitis, "
        "and Contact Dermatitis. It can also report that none of these "
        "was detected. It provides preliminary, informational output, "
        "not a medical diagnosis."
    ),
    "image_upload": (
        "Use a clear, well-lit close-up photo focused directly on the "
        "affected area, filling most of the frame. Photos taken from far "
        "away can miss small lesions. Avoid heavy filters, glare, blur, "
        "or shadows covering the skin. For the sharpest photo, use your "
        "phone's camera, then attach it with Choose photo or the image button "
        "and click Send."
    ),
    "trust_accuracy": (
        "Treat every Flamma result as a preliminary, informational insight, "
        "not a confirmed diagnosis. A qualified dermatologist should always "
        "confirm the condition, especially if symptoms are changing, "
        "painful, or worsening."
    ),
    "privacy": (
        "In this local installation, messages and uploaded photos are saved "
        "as conversation history on this computer. Clear history deletes the "
        "chats and photos associated with your browser. The image classifier "
        "runs locally. The optional Gemini chat endpoint, when configured and "
        "used, sends the question, retrieved information, and any supplied "
        "classification label and confidence to Google; it does not send the "
        "uploaded image itself."
    ),
}
