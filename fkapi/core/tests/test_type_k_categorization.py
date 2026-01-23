"""Tests for Type_K automatic categorization."""

from django.test import TestCase

from core.models import Type_K


class TypeKCategorizationTests(TestCase):
    """Test automatic categorization of Type_K when created."""

    def test_new_type_k_auto_categorizes(self):
        """Test that new Type_K instances are automatically categorized."""
        type_k = Type_K.objects.create(name="Home")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "match")
        self.assertEqual(type_k.category_order, 1)
        self.assertFalse(type_k.is_goalkeeper)
        self.assertEqual(type_k.order_priority, 1)  # Home has priority 1

    def test_gk_type_k_categorization(self):
        """Test that GK types are correctly identified."""
        type_k = Type_K.objects.create(name="GK Home")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "match")
        self.assertEqual(type_k.category_order, 1)
        self.assertTrue(type_k.is_goalkeeper)
        self.assertEqual(type_k.order_priority, 1)

    def test_training_type_k_categorization(self):
        """Test that training types are correctly categorized."""
        type_k = Type_K.objects.create(name="Training")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "training")
        self.assertEqual(type_k.category_order, 4)
        self.assertFalse(type_k.is_goalkeeper)

    def test_training_jacket_still_jacket(self):
        """Test that 'Training Jacket' is categorized as jacket, not training."""
        type_k = Type_K.objects.create(name="Training Jacket")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "jacket")
        self.assertEqual(type_k.category_order, 6)
        self.assertFalse(type_k.is_goalkeeper)

    def test_prematch_type_k_categorization(self):
        """Test that pre-match types are correctly categorized."""
        type_k = Type_K.objects.create(name="Pre-Match")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "prematch")
        self.assertEqual(type_k.category_order, 2)
        self.assertFalse(type_k.is_goalkeeper)

    def test_travel_type_k_categorization(self):
        """Test that travel/polo types are correctly categorized."""
        type_k = Type_K.objects.create(name="Travel")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "travel")
        self.assertEqual(type_k.category_order, 5)
        self.assertFalse(type_k.is_goalkeeper)

    def test_jacket_type_k_categorization(self):
        """Test that jacket types are correctly categorized."""
        type_k = Type_K.objects.create(name="Rain Jacket")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "jacket")
        self.assertEqual(type_k.category_order, 6)
        self.assertFalse(type_k.is_goalkeeper)

    def test_away_type_priority(self):
        """Test that Away has correct priority."""
        type_k = Type_K.objects.create(name="Away")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "match")
        self.assertEqual(type_k.order_priority, 2)  # Away has priority 2

    def test_third_type_priority(self):
        """Test that Third has correct priority."""
        type_k = Type_K.objects.create(name="Third")
        type_k.categorize()
        type_k.save()

        self.assertEqual(type_k.category, "match")
        self.assertEqual(type_k.order_priority, 3)  # Third has priority 3

    def test_categorize_method_returns_self(self):
        """Test that categorize() method returns self for chaining."""
        type_k = Type_K.objects.create(name="Home")
        result = type_k.categorize()

        self.assertIs(result, type_k)
        self.assertEqual(type_k.category, "match")
