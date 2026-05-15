from src.application.ports.crm_lookup_port import CrmLookupPort


class CrmLookupAdapter(CrmLookupPort):
    def lookup(self, crm_state: str, crm_number: str) -> dict | None:
        # The CFM Web Service (sistemas.cfm.org.br/listamedicos) requires a signed
        # agreement and an annual-fee Access Key (Resolução CFM 2.129/15).
        # There is no stable public endpoint that can be called without credentials.
        # Return None so callers treat the lookup as unavailable rather than an error.
        return None
