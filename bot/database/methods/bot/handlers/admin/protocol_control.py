import io
import logging

from aiogram import Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.formatting import Text, Code, Spoiler, Bold

from bot.database.methods.delete import delete_server
from bot.database.methods.get import (
    get_vds_id,
    get_server_id,
    get_keys_id,
    get_server
)
from bot.database.methods.insert import add_server
from bot.database.methods.update import (
    server_space_update,
    server_work_update,
    update_delete_users_server
)
from bot.database.models.main import Servers
from bot.handlers.admin.user_management import string_user_server
from bot.keyboards.inline.admin_inline import (
    choosing_connection,
    choosing_panel,
    choosing_vpn,
    protocol_list_menu,
    server_control, type_server_menu
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.callbackData import (
    ChoosingConnectionMethod,
    ChoosingPanel,
    ChoosingVPN,
    AddProtocol,
    ProtocolList,
    ServerWork,
    ServerUserList,
    ServerDelete, ChoosingTypeServer
)
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.service.edit_message import edit_message

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

state_admin_router = Router()


class AddServer(StatesGroup):
    input_ip = State()
    input_type_vpn = State()
    input_free_server = State()
    input_connect = State()
    input_panel = State()
    input_login = State()
    input_password = State()
    input_inbound_id = State()
    input_url_cert = State()


@state_admin_router.callback_query(AddProtocol.filter())
async def add_protocol(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: AddProtocol
):
    lang = await get_lang(call.from_user.id, state)
    await state.clear()
    await state.update_data(vds=callback_data.vds_id)
    if CONFIG.free_vpn:
        await edit_message(
            call.message,
            caption=_('server_input_type_server_text', lang),
            reply_markup=await type_server_menu(lang)
        )
    else:
        await state.update_data(free_server=False)
        await edit_message(
            call.message,
            caption=_('server_input_type_vpn_text', lang),
            reply_markup=await choosing_vpn(callback_data.vds_id, lang)
        )


@state_admin_router.callback_query(ChoosingTypeServer.filter())
async def input_ip(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChoosingTypeServer
):
    lang = await get_lang(call.from_user.id, state)
    await state.update_data(free_server=callback_data.type_server)
    data = await state.get_data()
    await edit_message(
        call.message,
        caption=_('server_input_type_vpn_text', lang),
        reply_markup=await choosing_vpn(data['vds'], lang)
    )


@state_admin_router.callback_query(ChoosingVPN.filter())
async def input_type_connect(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChoosingVPN):
    lang = await get_lang(call.from_user.id, state)
    await state.update_data(type_vpn=callback_data.type)
    if callback_data.type == 0:
        await edit_message(
            call.message,
            caption=_('server_input_url_cert_text', lang),
        )
        await state.set_state(AddServer.input_url_cert)
    elif callback_data.type == 1 or callback_data.type == 2:
        await edit_message(
            call.message,
            caption=_('server_input_ip_text', lang)
        )
        await state.set_state(AddServer.input_ip)
    else:
        await call.message.answer(
            _('server_error_choosing_type_connect_text', lang)
        )
        await state.clear()
    await call.answer()


@state_admin_router.message(AddServer.input_url_cert)
async def input_url_cert(message: Message, state: FSMContext):
    await state.update_data(outline_link=message.text.strip())
    user_data = await state.get_data()
    await create_new_protocol(message, state, user_data)
    await state.clear()


@state_admin_router.message(AddServer.input_ip)
async def input_ip(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    await state.update_data(ip=message.text.strip())
    await message.answer(
        _('server_input_choosing_type_connect_text', lang),
        reply_markup=await choosing_connection()
    )
    await state.set_state(AddServer.input_connect)


@state_admin_router.callback_query(
    ChoosingConnectionMethod.filter(),
    AddServer.input_connect
)
async def callback_connect(
        call: CallbackQuery,
        callback_data: ChoosingConnectionMethod,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    await state.update_data(connection_method=callback_data.connection)
    await call.message.answer(
        _('server_choosing_panel_control', lang),
        reply_markup=await choosing_panel()
    )
    await call.answer()
    await state.set_state(AddServer.input_panel)


@state_admin_router.callback_query(
    ChoosingPanel.filter(),
    AddServer.input_panel
)
async def input_id_connect(
        call: CallbackQuery,
        callback_data: ChoosingConnectionMethod,
        state: FSMContext
):
    await state.update_data(panel=callback_data.panel)
    await call.message.answer(_(
        'server_input_id_connect_text',
        await get_lang(call.from_user.id, state)
    ))
    await call.answer()
    await state.set_state(AddServer.input_inbound_id)


@state_admin_router.message(AddServer.input_inbound_id)
async def input_inbound_id_handler(message: Message, state: FSMContext):
    if message.text.strip().isdigit():
        await state.update_data(inbound_id=int(message.text.strip()))
    else:
        await message.answer('? Connection ID is not a number')
        return
    await message.answer(_(
        'server_input_login_text',
        await get_lang(message.from_user.id, state))
    )
    await state.set_state(AddServer.input_login)


@state_admin_router.message(AddServer.input_login)
async def input_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await message.answer(_(
        'server_input_password_panel_text',
        await get_lang(message.from_user.id, state)
    )
    )
    await state.set_state(AddServer.input_password)


@state_admin_router.message(AddServer.input_password)
async def input_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    user_data = await state.get_data()
    await create_new_protocol(message, state, user_data)
    await state.clear()


async def create_new_protocol(message, state, user_data):
    lang = await get_lang(message.from_user.id, state)
    del user_data['lang']
    try:
        server = Servers.create_server(user_data)
        server_manager = ServerManager(server)
        await server_manager.login()
        connect = await server_manager.get_all_user()
        if connect is None:
            raise ModuleNotFoundError
    except Exception as e:
        await message.answer(
            _('server_error_connect', lang)
        )
        log.error(e, 'state_server.py not connect server')
        await show_list_protocol(message, state, lang, user_data['vds'])
        return
    try:
        await add_server(server)
    except Exception as e:
        await message.answer(
            _('server_error_write_db_name', lang)
        )
        log.error(e, 'state_server.py not read server database')
        await show_list_protocol(message, state, lang, user_data['vds'])
        return
    await message.answer(
        _('server_add_success', lang)
    )
    await show_list_protocol(message, state, lang, user_data['vds'])


async def show_list_protocol(
        message: Message, state: FSMContext, lang, vds_id
):
    await state.clear()
    vds = await get_vds_id(vds_id)
    await message.answer(
        _('protocol_list_text', lang)
        .format(vds_ip=vds.ip),
        reply_markup=await protocol_list_menu(
            vds.location, vds.id, vds.servers, lang
        )
    )


@state_admin_router.callback_query(ProtocolList.filter())
async def protocol_control_call(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ProtocolList
):
    lang = await get_lang(call.from_user.id, state)
    protocol = await get_server_id(callback_data.protocol_id)
    space = 0
    try:
        client_server = await get_static_client(protocol)
        space = len(client_server)
        if not await server_space_update(protocol.id, space):
            raise ("Failed to update the data about "
                   "the free space on the server")
        connect = True
    except Exception as e:
        log.error(e, 'error connecting to server')
        connect = False
    if connect:
        space_text = _('protocol_server_text', lang).format(
            space=space
        )
    else:
        space_text = _('server_not_connect_admin', lang)
    if protocol.work:
        work_text = _("server_use_s", lang)
    else:
        work_text = _("server_not_use_s", lang)
    type_server = (
        _("server_type_free", lang)) \
        if protocol.free_server else (
        _("server_type_not_free", lang)
    )
    if protocol.type_vpn == 0:
        text = Text(
            '\n', _('server_type_vpn_s', lang),
            ServerManager.VPN_TYPES.get(protocol.type_vpn).NAME_VPN, '\n',
            _('server_type_free_vds_s', lang), Bold(type_server), '\n',
            _('server_outline_connect_s', lang), Code(protocol.outline_link),
            '\n', work_text, '\n', space_text
        )
    else:
        text = Text(
            '\n', _('server_type_vpn_s', lang),
            ServerManager.VPN_TYPES.get(protocol.type_vpn).NAME_VPN, '\n',
            _('server_type_free_vds_s', lang), Bold(type_server), '\n',
            _('server_adress_s', lang), Code(protocol.ip), '\n',
            _('server_type_connect_s', lang),
            f'{"Https" if protocol.connection_method else "Http"}', '\n',
            _('server_panel_control_s', lang),
            f'{"Alireza ??" if protocol.panel == "alireza" else "Sanaei ??"}',
            '\n',
            _('server_id_connect_s', lang), Bold(protocol.inbound_id), '\n',
            _('server_login_s', lang), Bold(protocol.login), '\n',
            _('server_password_s', lang), Spoiler(protocol.password), '\n',
            work_text, '\n', space_text
        )
    try:
        await call.message.edit_text(
            **text.as_kwargs(),
            reply_markup=await server_control(protocol, lang)
        )
    except Exception as e:
        log.error(e, 'error edit protocol')
        await call.message.answer(
            **text.as_kwargs(),
            reply_markup=await server_control(protocol, lang)
        )


async def get_static_client(server):
    server_manager = ServerManager(server)
    await server_manager.login()
    return await server_manager.get_all_user()


@state_admin_router.callback_query(ServerWork.filter())
async def callback_work_server(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ServerWork
):
    lang = await get_lang(call.from_user.id, state)
    protocol = await get_server_id(callback_data.id_protocol)
    text_working = _('server_use_active', lang).format(
        type_protocol=ServerManager.VPN_TYPES.get(protocol.type_vpn).NAME_VPN,
    )
    text_uncorking = _('server_not_use_active', lang).format(
        type_protocol=ServerManager.VPN_TYPES.get(protocol.type_vpn).NAME_VPN,
    )
    text_message = text_working if callback_data.work else text_uncorking
    await server_work_update(callback_data.id_protocol, callback_data.work)
    await edit_message(
        call.message,
        caption=text_message
    )
    await show_list_protocol(call.message, state, lang, protocol.vds)


@state_admin_router.callback_query(ServerUserList.filter())
async def call_list_server(
        call: CallbackQuery,
        callback_data: ServerUserList,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    protocol = await get_server(callback_data.id_protocol)
    try:
        client_stats = await get_static_client(protocol)
    except Exception as e:
        await call.message.answer(_('server_not_connect_admin', lang))
        await call.answer()
        log.error(e, 'server not connect')
        return
    try:
        if protocol.type_vpn == 0:
            client_id = []
            all_client = list({client.name for client in client_stats})
            for client in client_stats:
                client_sr = client.name.split('.')
                if client_sr[0].isdigit() and len(client_sr) == 2:
                    client_id.append(int(client_sr[1]))
                    all_client.remove(client.name)
        else:
            client_id = []
            all_client = list({client['email'] for client in client_stats})
            for client in client_stats:
                client_sr = client['email'].split('.')
                if client_sr[0].isdigit() and len(client_sr) == 2:
                    client_id.append(int(client_sr[1]))
                    all_client.remove(client['email'])
        bot_client = await get_keys_id(client_id)
        if not callback_data.action:
            await delete_users_server(call.message, protocol, bot_client, lang)
            await edit_message(
                call.message,
                caption=_('key_delete_server', lang)
                .format(
                    name=ServerManager.VPN_TYPES
                    .get(protocol.type_vpn).NAME_VPN
                ),
            )
            await show_list_protocol(call.message, state, lang, protocol.vds)
            return
        text_client = await get_text_client(all_client, bot_client, lang)
    except Exception as e:
        await call.message.answer(_('error_get_users_bd_text', lang))
        await call.answer()
        log.error(e, 'error get users BD')
        return
    if text_client == '':
        await call.message.answer(_('file_server_user_none', lang))
        await call.answer()
        return
    file_stream = io.BytesIO(text_client.encode()).getvalue()
    input_file = BufferedInputFile(file_stream, 'Clients_server.txt')
    try:
        await call.message.answer_document(
            input_file,
            caption=_('file_list_users_server', lang)
            .format(
                name=ServerManager.VPN_TYPES
                .get(protocol.type_vpn).NAME_VPN
            )
        )
    except Exception as e:
        await call.message.answer(_('error_file_list_users_server', lang))
        log.error(e, 'error file send Clients_server.txt')
    await call.answer()


async def get_text_client(all_client, bot_client, lang):
    text_client = ''
    count = 1
    for key in bot_client:
        text_client += await string_user_server(key.person, count, lang)
        count += 1
    for unknown_client in all_client:
        text_client += _('not_found_key', lang).format(
            unknown_client=unknown_client
        )
    return text_client


async def delete_users_server(m, protocol, keys, lang):
    server_manager = ServerManager(protocol)
    await server_manager.login()
    for key in keys:
        try:
            await server_manager.delete_client(key.user_tgid, key.id)
        except Exception as e:
            log.error(e, 'not delete users server')
            await m.answer(_('error_delete_all_users_server', lang))
            return False
    await update_delete_users_server(protocol)
    await server_space_update(protocol.id, 0)
    return True


@state_admin_router.callback_query(ServerDelete.filter())
async def delete_server_call(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ServerDelete
):
    lang = await get_lang(call.from_user.id, state)
    protocol = await get_server(callback_data.id_protocol)
    try:
        await delete_server(callback_data.id_protocol)
    except Exception as e:
        await call.message.answer(
            _('server_error_delete', lang)
        )
        log.error(e, 'error delete server')
        return
    await edit_message(
        call.message,
        caption=_('server_delete_success', lang)
    )
    await show_list_protocol(call.message, state, lang, protocol.vds)