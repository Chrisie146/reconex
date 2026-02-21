"""
Generic / Unknown bank plugin – fallback adapter.
"""

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class GenericPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="generic",
        bank_name="Generic / Unknown",
        pdf_keywords=[],
        csv_header_patterns={},
        date_formats=["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"],
        date_regex="",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        # Generic never wins detection – only used as explicit fallback
        return 0.0

    def get_adapter(self):
        from services.bank_adapters import GenericAdapter
        return GenericAdapter()
