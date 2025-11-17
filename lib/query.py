import aiohttp
import re
import time
import logging
import asyncio
from typing import Any
from libprobe.asset import Asset
from .connector import get_connector
from .version import __version__


TIME_OFFSET = 120  # seconds for token to expire before actual expiration
IS_URL = re.compile(r'^https?\:\/\/', re.IGNORECASE)
USER_AGENT = f'InfraSonarVeeamBrProbe/{__version__}'
TOKEN_CACHE: dict[tuple[str, str, str, str], tuple[float, str, str]] = {}
LOCK = asyncio.Lock()


async def get_new_token(api_url: str,
                        api_version: str,
                        grant_type: str,
                        username: str,
                        password: str,
                        verify_ssl: bool) -> tuple[int, str, str]:
    data = {
        'grant_type': grant_type,
        'username': username,
        'password': password,
    }
    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-API-Version': api_version,
    }
    url = f'{api_url}/oauth2/token'
    async with aiohttp.ClientSession(connector=get_connector()) as session:
        async with session.post(
                url,
                data=data,
                headers=headers,
                ssl=verify_ssl) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return (
                data['expires_in'],
                data['access_token'],
                data['refresh_token'],
            )


async def get_refresh_token(api_url: str,
                            api_version: str,
                            grant_type: str,
                            refresh_token: str,
                            verify_ssl: bool) -> tuple[int, str, str]:
    data = {
        'grant_type': grant_type,
        'refresh_token': refresh_token,
    }
    headers = {
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-API-Version': api_version,
    }
    url = f'{api_url}/oauth2/token'
    async with aiohttp.ClientSession(connector=get_connector()) as session:
        async with session.post(
                url,
                data=data,
                headers=headers,
                ssl=verify_ssl) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return (
                data['expires_in'],
                data['access_token'],
                data['refresh_token'],
            )


async def get_token(api_url: str,
                    api_version: str,
                    grant_type: str,
                    username: str,
                    password: str,
                    verify_ssl: bool,
                    force_new_token: bool) -> tuple[str, bool]:
    async with LOCK:
        key = (api_url, api_version, username, password)
        now = time.time()
        expire_ts, token, refresh_token = TOKEN_CACHE.get(key, (0.0, '', ''))
        is_new = False
        if force_new_token or now > expire_ts:
            if refresh_token:
                expires_in, token, refresh_token = \
                    await get_refresh_token(
                        api_url=api_url,
                        api_version=api_version,
                        grant_type=grant_type,
                        refresh_token=refresh_token,
                        verify_ssl=verify_ssl)
            else:
                expires_in, token, refresh_token = \
                    await get_new_token(
                        api_url=api_url,
                        api_version=api_version,
                        grant_type=grant_type,
                        username=username,
                        password=password,
                        verify_ssl=verify_ssl)
            logging.debug(f'Token expires in {expires_in} seconds')
            expire_ts = now + expires_in - TIME_OFFSET
            TOKEN_CACHE[key] = (expire_ts, token, refresh_token)
            is_new = True

    return token, is_new


async def _query(
        asset: Asset,
        local_config: dict,
        config: dict,
        force_new_token: bool) -> tuple[str, str, str, bool, bool]:
    grant_type = local_config.get('grantType', 'password')
    username = local_config.get('username')
    password = local_config.get('password')

    assert grant_type == 'password', (
        'Only Grant Type `password` is supported, '
        'please contact InfraSonar support for other authentication methods')

    assert username, (
        'Username missing, '
        'please provide the Username as `username` in the appliance config')

    assert password, (
        'Password missing, '
        'please provide the Password as `password` in the appliance config')

    address = config.get('address') or asset.name
    verify_ssl = config.get('verifySSL', False)
    port = config.get('port', 9419)
    api_version = config.get('apiVersion', '1.2.-rev1')

    assert api_version.startswith('1'), (
        f'Only API Version 1.X.X is supported (got: {api_version})')

    if not IS_URL.match(address):
        address = f'https://{address}'

    api_url = f'{address}:{port}'
    logging.debug(f'Using API Url: {api_url}')

    token, is_new = await get_token(
        api_url=api_url,
        api_version=api_version,
        grant_type=grant_type,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        force_new_token=force_new_token)

    return api_url, api_version, token, verify_ssl, is_new


async def query_multi(
        asset: Asset,
        local_config: dict,
        config: dict,
        req: str,
        params: dict[str, Any] = {},
        force_new_token: bool = False) -> list[dict[str, Any]]:
    api_url, api_version, token, verify_ssl, is_new = await _query(
        asset,
        local_config,
        config,
        force_new_token)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-API-Version': api_version,
    }

    assert req.startswith('/')
    url = f'{api_url}/v1{req}'

    results = []

    while True:
        async with aiohttp.ClientSession(connector=get_connector()) as session:
            async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    ssl=verify_ssl) as resp:
                if is_new is False and resp.status == 401:
                    # Retry when using an old token and 401
                    return await query_multi(
                        asset=asset,
                        local_config=local_config,
                        config=config,
                        req=req,
                        params=params,
                        force_new_token=True)

                resp.raise_for_status()
                data = await resp.json()

        results.extend(data['data'])

        total = data['pagination']['total']
        if len(results) >= total:
            break

        params['skip'] = len(results)

    return results


async def query(
        asset: Asset,
        local_config: dict,
        config: dict,
        req: str,
        params: dict[str, Any] = {},
        force_new_token: bool = False) -> dict[str, Any]:
    api_url, api_version, token, verify_ssl, is_new = await _query(
        asset,
        local_config,
        config,
        force_new_token)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-API-Version': api_version,
    }

    assert req.startswith('/')
    url = f'{api_url}/v1{req}'

    async with aiohttp.ClientSession(connector=get_connector()) as session:
        async with session.get(
                url,
                headers=headers,
                params=params,
                ssl=verify_ssl) as resp:
            if is_new is False and resp.status == 401:
                # Retry when using an old token and 401
                return await query(
                    asset=asset,
                    local_config=local_config,
                    config=config,
                    req=req,
                    force_new_token=True)

            resp.raise_for_status()
            data = await resp.json()

    return data
