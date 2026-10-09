import json


class ExpertSystem:

    def __init__(self, rules_path="data/expert_rules.json"):

        with open(rules_path, "r", encoding="utf-8") as file:
            self.rule_data = json.load(file)

        self.rules = self.rule_data.get("rules", [])

        self.supported_diseases = set(
            self.rule_data.get("supported_diseases", [])
        )


    def evaluate(self, conversation_data):
        """
        Evaluate screening information and the image classification
        against dermatologist-validated expert rules.

        Clinical rules will be added to expert_rules.json only after
        validation.
        """

        classification = conversation_data.get("classification")
        confidence = conversation_data.get(
            "classification_confidence"
        )

        # ------------------------------------------------------
        # Require image classification
        # ------------------------------------------------------

        if classification is None:
            return {
                "success": False,
                "status": "awaiting_classification",
                "message": (
                    "An image classification result is required "
                    "before expert-system evaluation."
                ),
                "matched_rules": []
            }

        # ------------------------------------------------------
        # Validate disease
        # ------------------------------------------------------

        normalized_disease = (
            str(classification)
            .lower()
            .strip()
            .replace("_", " ")
        )

        if normalized_disease not in self.supported_diseases:
            return {
                "success": False,
                "status": "unsupported_classification",
                "message": (
                    "The image classification is not supported "
                    "by the expert system."
                ),
                "matched_rules": []
            }

        # ------------------------------------------------------
        # Validate classifier confidence
        # ------------------------------------------------------

        try:
            confidence = float(confidence)

        except (TypeError, ValueError):
            return {
                "success": False,
                "status": "invalid_confidence",
                "message": (
                    "The image classification confidence is invalid."
                ),
                "matched_rules": []
            }

        if confidence < 0.0 or confidence > 1.0:
            return {
                "success": False,
                "status": "invalid_confidence",
                "message": (
                    "The image classification confidence must "
                    "be between 0 and 1."
                ),
                "matched_rules": []
            }

        # ------------------------------------------------------
        # Evaluate available rules
        # ------------------------------------------------------

        matched_rules = []

        for rule in self.rules:

            if self._matches_rule(
                rule,
                conversation_data,
                normalized_disease
            ):
                matched_rules.append(rule)

        # ------------------------------------------------------
        # No validated rules yet
        # ------------------------------------------------------

        if not matched_rules:
            return {
                "success": True,
                "status": "no_matching_validated_rule",
                "disease": normalized_disease,
                "classification_confidence": confidence,
                "matched_rules": [],
                "recommendations": [],
                "referral": None,
                "message": (
                    "The classification was received successfully, "
                    "but no dermatologist-validated expert rule "
                    "matched this case."
                )
            }

        # ------------------------------------------------------
        # Build result from matched rules
        # ------------------------------------------------------

        recommendations = []
        referrals = []

        for rule in matched_rules:

            recommendation = rule.get("recommendation")

            if (
                recommendation
                and recommendation not in recommendations
            ):
                recommendations.append(recommendation)

            referral = rule.get("referral")

            if referral and referral not in referrals:
                referrals.append(referral)

        return {
            "success": True,
            "status": "rules_matched",
            "disease": normalized_disease,
            "classification_confidence": confidence,
            "matched_rules": [
                rule.get("id")
                for rule in matched_rules
            ],
            "recommendations": recommendations,
            "referral": referrals,
            "message": (
                "The expert-system evaluation completed "
                "successfully."
            )
        }


    def _matches_rule(
        self,
        rule,
        conversation_data,
        normalized_disease
    ):
        """
        Generic rule matcher.

        Only fields explicitly defined inside a rule's
        conditions are checked.
        """

        conditions = rule.get("conditions", {})

        # Disease condition
        disease = conditions.get("classification")

        if disease is not None:

            normalized_rule_disease = (
                str(disease)
                .lower()
                .strip()
                .replace("_", " ")
            )

            if normalized_rule_disease != normalized_disease:
                return False

        # Severity condition
        severity = conditions.get("severity")

        if severity is not None:

            conversation_severity = conversation_data.get(
                "severity"
            )

            if conversation_severity is None:
                return False

            if (
                str(conversation_severity).lower().strip()
                != str(severity).lower().strip()
            ):
                return False

        # Medication condition
        medication = conditions.get("medication")

        if medication is not None:

            conversation_medication = conversation_data.get(
                "medication"
            )

            if conversation_medication is None:
                return False

            if (
                str(conversation_medication).lower().strip()
                != str(medication).lower().strip()
            ):
                return False

        return True