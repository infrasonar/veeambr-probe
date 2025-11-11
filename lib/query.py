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
USER_AGENT = f'InfraSonarVeeamProbe/{__version__}'
TOKEN_CACHE: dict[tuple[str, str], tuple[float, str]] = {}
LOCK = asyncio.Lock()


async def get_new_token(api_url: str,
                        grant_type: str,
                        client_id: str,
                        client_secret: str,
                        username: str,
                        password: str,
                        disable_antiforgery_token: bool,
                        verify_ssl: bool) -> tuple[int, str]:
    dat = 'true' if disable_antiforgery_token else 'false'
    data = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password,
        'disable_antiforgery_token': dat
    }
    headers = {
        # 'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    url = f'{api_url}/token'
    async with aiohttp.ClientSession(connector=get_connector()) as session:
        async with session.post(
                url,
                data=data,
                headers=headers,
                ssl=verify_ssl) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data['expires_in'], data['access_token']


async def get_token(api_url: str,
                    grant_type: str,
                    client_id: str,
                    client_secret: str,
                    username: str,
                    password: str,
                    disable_antiforgery_token: bool,
                    verify_ssl: bool,
                    force_new_token: bool) -> tuple[str, bool]:
    async with LOCK:
        key = (client_id, username)
        now = time.time()
        expire_ts, token = TOKEN_CACHE.get(key, (0.0, ''))
        is_new = False
        if force_new_token or now > expire_ts:
            expires_in, token = \
                await get_new_token(
                    api_url=api_url,
                    grant_type=grant_type,
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                    disable_antiforgery_token=disable_antiforgery_token,
                    verify_ssl=verify_ssl)
            logging.debug(f'Token expires in {expires_in} seconds')
            expire_ts = now + expires_in - TIME_OFFSET
            TOKEN_CACHE[key] = (expire_ts, token)
            is_new = True

    return token, is_new


async def _query(
        asset: Asset,
        asset_config: dict,
        check_config: dict,
        req: str,
        force_new_token: bool) -> tuple[str, str, str, bool, bool]:
    grant_type = asset_config.get('grantType', 'password')
    client_id = asset_config.get('clientId')
    client_secret = asset_config.get('secret')
    username = asset_config.get('username')
    password = asset_config.get('password')
    disable_antiforgery_token = \
        asset_config.get('disableAntiforgeryToken', True)

    assert grant_type == 'password', (
        'Only Grant Type `password` is supported, '
        'please contact InfraSonar support for other authentication methods')

    assert client_id, (
        'Client ID is missing, '
        'please provide the Client ID as `clientId` in the appliance config')

    assert client_secret, (
        'Client Secret is missing, '
        'please provide the Client Secret as `secret` in the appliance config')

    assert username, (
        'Username missing, '
        'please provide the Username as `username` in the appliance config')

    assert password, (
        'Password missing, '
        'please provide the Password as `password` in the appliance config')

    assert isinstance(disable_antiforgery_token, bool), (
        'Property `disableAntiforgeryToken` must be a boolean if provided '
        'in the appliance config')

    address = check_config.get('address') or asset.name
    verify_ssl = check_config.get('verifySSL', False)
    port = check_config.get('port', 4443)
    api_version = check_config.get('apiVersion', 'v8')

    assert api_version == 'v8', (
        f'Only API Version 8 is supported (got: {api_version})')

    if not IS_URL.match(address):
        address = f'https://{address}'

    api_url = f'{address}:{port}'
    logging.debug(f'Using API Url: {api_url}')

    token, is_new = await get_token(
        api_url=f'{api_url}/{api_version}',
        grant_type=grant_type,
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        disable_antiforgery_token=disable_antiforgery_token,
        verify_ssl=verify_ssl,
        force_new_token=force_new_token)

    return api_url, api_version, token, verify_ssl, is_new


async def query_multi(
        asset: Asset,
        asset_config: dict,
        check_config: dict,
        req: str,
        force_new_token: bool = False) -> list[dict[str, Any]]:
    api_url, api_version, token, verify_ssl, is_new = await _query(
        asset,
        asset_config,
        check_config,
        req,
        force_new_token)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    assert req.startswith('/')
    url = f'{api_url}/{api_version}{req}'

    results = []

    while True:
        async with aiohttp.ClientSession(connector=get_connector()) as session:
            async with session.get(
                    url,
                    headers=headers,
                    ssl=verify_ssl) as resp:
                if is_new is False and resp.status == 401:
                    # Retry when using an old token and 401
                    return await query_multi(
                        asset=asset,
                        asset_config=asset_config,
                        check_config=check_config,
                        req=req,
                        force_new_token=True)

                resp.raise_for_status()
                data = await resp.json()

        results.extend(data.get('results', []))

        next = data.get('_links', {}).get('next', {}).get('href')
        if not next:
            break

        url = f'{api_url}{next}'

    return results


async def query(
        asset: Asset,
        asset_config: dict,
        check_config: dict,
        req: str,
        force_new_token: bool = False) -> dict[str, Any]:
    api_url, api_version, token, verify_ssl, is_new = await _query(
        asset,
        asset_config,
        check_config,
        req,
        force_new_token)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    assert req.startswith('/')
    url = f'{api_url}/{api_version}{req}'

    async with aiohttp.ClientSession(connector=get_connector()) as session:
        async with session.get(
                url,
                headers=headers,
                ssl=verify_ssl) as resp:
            if is_new is False and resp.status == 401:
                # Retry when using an old token and 401
                return await query(
                    asset=asset,
                    asset_config=asset_config,
                    check_config=check_config,
                    req=req,
                    force_new_token=True)

            resp.raise_for_status()
            data = await resp.json()

    return data
