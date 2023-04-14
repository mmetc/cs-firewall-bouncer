"""
Full integration test with a real Crowdsec running in Docker
"""

import contextlib
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'deb: tests for build/install/configure a debian packages'
    )
    config.addinivalue_line(
        'markers', 'rpm: tests for build/install/configure rpm packages'
    )
    config.addinivalue_line(
        'markers', 'iptables: tests iptables (requires root)'
    )
    config.addinivalue_line(
        'markers', 'nftables: tests nftables (requires root)'
    )


# provide the name of the bouncer binary to test
@pytest.fixture(scope='session')
def bouncer_under_test():
    return 'crowdsec-firewall-bouncer'


# Create a lapi container, register a bouncer and run it with the updated config.
# - Return context manager that yields a tuple of (bouncer, lapi)
@pytest.fixture(scope='session')
def bouncer_with_lapi(bouncer, crowdsec, fw_cfg_factory, api_key_factory, tmp_path_factory, bouncer_binary):
    @contextlib.contextmanager
    def closure(config_lapi=None, config_bouncer=None, api_key=None):
        if config_bouncer is None:
            config_bouncer = {}
        if config_lapi is None:
            config_lapi = {}
        # can be overridden by config_lapi + config_bouncer
        api_key = api_key_factory()
        env = {
            'BOUNCER_KEY_custom': api_key,
        }
        try:
            env.update(config_lapi)
            with crowdsec(environment=env) as lapi:
                lapi.wait_for_http(8080, '/health')
                port = lapi.probe.get_bound_port('8080')
                cfg = fw_cfg_factory()
                cfg.setdefault('crowdsec_config', {})
                cfg['api_url'] = f'http://localhost:{port}/'
                cfg['api_key'] = api_key
                cfg.update(config_bouncer)
                with bouncer(bouncer_binary, cfg) as cb:
                    yield cb, lapi
        finally:
            pass

    yield closure


_default_config = {
    'log_mode': 'stdout',
    'log_level': 'info',
}


@pytest.fixture(scope='session')
def fw_cfg_factory():
    def closure(**kw):
        cfg = _default_config.copy()
        cfg |= kw
        return cfg | kw
    yield closure
