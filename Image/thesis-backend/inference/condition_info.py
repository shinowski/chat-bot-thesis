CONDITION_INFO = {
    "atopic_dermatitis": {
        "display_name": "Atopic Dermatitis",
        "description": "A chronic inflammatory skin condition that commonly causes dryness, itching, redness, and irritated patches. It often appears on areas such as the face, hands, elbows, and knees and may flare periodically.",
        "summary": "The image was classified as Atopic Dermatitis based on overall visual similarity to atopic dermatitis images in the model's training data.",
        "why": "The model's learned patterns most closely matched examples of atopic dermatitis it was trained on. This reflects overall color, texture, and structural similarity across the image — the model does not identify or name specific clinical features, only statistical patterns.",
        "recommendations": "Consider using fragrance-free moisturizers, avoiding known triggers such as harsh soaps or extreme temperatures, and scheduling a visit with a dermatologist to confirm the diagnosis and discuss treatment options.",
    },
    "contact_dermatitis": {
        "display_name": "Contact Dermatitis",
        "description": "An inflammatory skin reaction that can occur after contact with an irritating substance or an allergen. It may cause redness, itching, swelling, dryness, or a rash in the area that was exposed.",
        "summary": "The image was classified as Contact Dermatitis based on overall visual similarity to contact dermatitis images in the model's training data.",
        "why": "The model's learned patterns most closely matched examples of contact dermatitis it was trained on. This reflects overall color, texture, and structural similarity, the model does not identify or name specific clinical features, only statistical patterns.",
        "recommendations": "Try to identify and avoid the substance that may have triggered the reaction, keep the area clean and moisturized, and see a dermatologist if the irritation persists or worsens.",
    },
    "lichen_planus": {
        "display_name": "Lichen Planus",
        "description": "An inflammatory skin condition that can cause itchy, purplish, flat-topped bumps or patches. It commonly affects the wrists, ankles, lower back, and other areas of the skin.",
        "summary": "The image was classified as Lichen Planus based on overall visual similarity to lichen planus images in the model's training data.",
        "why": "The model's learned patterns most closely matched examples of lichen planus it was trained on. This reflects overall color, texture, and structural similarity, the model does not identify or name specific clinical features, only statistical patterns.",
        "recommendations": "Avoid scratching the affected area, note whether the patches spread or change over time, and consult a dermatologist for confirmation and treatment options.",
    },
    "psoriasis": {
        "display_name": "Psoriasis",
        "description": "A chronic inflammatory skin condition that causes areas of the skin to become red, thickened, and covered with silvery-white scales. It commonly affects the elbows, knees, scalp, and other areas, although it can occur elsewhere.",
        "summary": "The image was classified as Psoriasis based on overall visual similarity to psoriasis images in the model's training data.",
        "why": "The model's learned patterns most closely matched examples of psoriasis it was trained on. This reflects overall color, texture, and structural similarity, the model does not identify or name specific clinical features (such as plaque type or scale texture), only statistical patterns learned from the training images available to it.",
        "recommendations": "Moisturize regularly, avoid known triggers such as stress and skin trauma, and schedule a visit with a dermatologist to confirm the diagnosis and discuss treatment options.",
    },
    "rosacea": {
        "display_name": "Rosacea",
        "description": "A chronic skin condition that commonly affects the face and may cause persistent redness, flushing, visible blood vessels, and sometimes small red bumps or pustules. Symptoms may become more noticeable after certain triggers.",
        "summary": "The image was classified as Rosacea based on overall visual similarity to rosacea images in the model's training data.",
        "why": "The model's learned patterns most closely matched examples of rosacea it was trained on. This reflects overall color, texture, and structural similarity, the model does not identify or name specific clinical features, only statistical patterns.",
        "recommendations": "Identify and avoid common triggers such as sun exposure, spicy food, or alcohol, use gentle skincare products, and consult a dermatologist for confirmation and treatment options.",
    },
    "normal_skin": {
        "display_name": "No Supported Condition Detected",
        "description": "This tool screens close-up photos for five specific skin conditions, and none of them was detected in this image. This is not a clearance: it does not confirm that the skin is healthy, and it cannot rule out other conditions. If you have a spot or symptom that concerns you, consult a qualified healthcare professional.",
        "summary": "The image's overall visual pattern did not match any of the five conditions this tool screens for, and was closest to the unaffected skin images in the model's training data.",
        "why": "The model's learned patterns did not match any of the five supported conditions. This is a pattern match against its training images, not a clinical clearance, and the model can miss small or distant lesions and conditions outside its scope.",
        "recommendations": "If a spot, bump, or area of skin concerns you, consult a dermatologist directly, whatever this result says. For best results, retake the photo as a close-up in good light.",
    },
}
