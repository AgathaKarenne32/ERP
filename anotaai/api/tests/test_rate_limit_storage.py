from app.core.config import Settings
from app.core.config import settings as settings_carregado
from app.core.rate_limit import limiter


def test_rate_limit_storage_uri_default_aponta_para_redis():
    """Item 8 do plano de próxima onda: em produção o storage do rate limit
    precisa ser compartilhado (Redis) entre réplicas, não em memória por
    processo — em memória, N réplicas multiplicam o limite efetivo por N."""
    assert Settings.model_fields["rate_limit_storage_uri"].default == "redis://redis:6379/2"


def test_limiter_usa_storage_uri_configurado():
    """O limiter não deve hardcodar o storage: tem que ler de settings, senão
    não dá pra trocar pra memory:// nos testes/CI sem Redis real."""
    assert limiter._storage_uri == settings_carregado.rate_limit_storage_uri
