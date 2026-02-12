import unittest
from datetime import datetime
from services.matcher import score_match, find_best_matches

class TestMatcher(unittest.TestCase):

    def test_score_match_exact_amount(self):
        invoice = {
            'supplier_name': 'Supplier A',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Supplier A',
            'date': datetime(2023, 10, 1),
            'amount': 100.00
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['classification'], 'High')
        self.assertTrue(result['matched']['amount'])
        self.assertTrue(result['matched']['date'])
        self.assertTrue(result['matched']['supplier'])

    def test_score_match_close_amount(self):
        invoice = {
            'supplier_name': 'Supplier A',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Supplier A',
            'date': datetime(2023, 10, 1),
            'amount': 100.50
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 100)  # 50 + 25 (date) + 25 (supplier)
        self.assertEqual(result['classification'], 'High')

    def test_score_match_date_within_7_days(self):
        invoice = {
            'supplier_name': 'Supplier A',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Supplier A',
            'date': datetime(2023, 10, 5),
            'amount': 100.00
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 100)  # 50 + 25 + 25
        self.assertTrue(result['matched']['date'])

    def test_score_match_date_outside_7_days(self):
        invoice = {
            'supplier_name': 'Supplier A',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Supplier A',
            'date': datetime(2023, 10, 10),
            'amount': 100.00
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 75)  # 50 + 0 + 25
        self.assertFalse(result['matched']['date'])

    def test_score_match_fuzzy_supplier(self):
        invoice = {
            'supplier_name': 'Supplier ABC Ltd',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Supplier ABC Limited',
            'date': datetime(2023, 10, 1),
            'amount': 100.00
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 100)  # 50 + 25 + 25 (cleaned to same)

    def test_score_match_no_match(self):
        invoice = {
            'supplier_name': 'Supplier A',
            'invoice_date': datetime(2023, 10, 1),
            'total_amount': 100.00
        }
        txn = {
            'description': 'Payment to Different Company',
            'date': datetime(2023, 11, 1),
            'amount': 50.00
        }
        result = score_match(invoice, txn)
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['classification'], 'Low')

    def test_find_best_matches(self):
        invoices = [
            {
                'id': 1,
                'supplier_name': 'Supplier A',
                'invoice_date': datetime(2023, 10, 1),
                'total_amount': 100.00
            },
            {
                'id': 2,
                'supplier_name': 'Supplier B',
                'invoice_date': datetime(2023, 10, 2),
                'total_amount': 200.00
            }
        ]
        txns = [
            {
                'id': 1,
                'description': 'Payment to Supplier A',
                'date': datetime(2023, 10, 1),
                'amount': 100.00
            },
            {
                'id': 2,
                'description': 'Payment to Supplier B',
                'date': datetime(2023, 10, 2),
                'amount': 200.00
            }
        ]
        matches = find_best_matches(invoices, txns)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]['invoice_id'], 1)
        self.assertEqual(matches[0]['transaction_id'], 1)
        self.assertEqual(matches[1]['invoice_id'], 2)
        self.assertEqual(matches[1]['transaction_id'], 2)

if __name__ == '__main__':
    unittest.main()