"""
Bank Plugins – Auto-discovery and registration.

Import this package to ensure all bank plugins are registered with the BankRegistry.
"""

from services.bank_plugins.registry import BankRegistry

# Import all plugins – each module-level class is instantiated and registered below.
from services.bank_plugins.standard_bank import StandardBankPlugin
from services.bank_plugins.absa import ABSAPlugin
from services.bank_plugins.capitec import CapitecPlugin
from services.bank_plugins.fnb import FNBPlugin
from services.bank_plugins.nedbank import NedbankPlugin
from services.bank_plugins.investec import InvestecPlugin
from services.bank_plugins.discovery import DiscoveryPlugin
from services.bank_plugins.generic import GenericPlugin


def _register_all() -> None:
    """Register every built-in bank plugin."""
    for plugin_cls in [
        StandardBankPlugin,
        ABSAPlugin,
        CapitecPlugin,
        FNBPlugin,
        NedbankPlugin,
        InvestecPlugin,
        DiscoveryPlugin,
        GenericPlugin,
    ]:
        plugin = plugin_cls()
        BankRegistry.register(plugin)


# Auto-register on import
_register_all()
