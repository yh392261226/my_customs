#!/usr/bin/env python3

import iterm2
# This script was created with the "basic" environment which does not support adding dependencies
# with pip.


async def async_getTmuxConnection(stab):
    if isinstance(stab, iterm2.Session):
        session = stab
    elif isinstance(stab, iterm2.Tab):
        session = stab.current_session
    else:
        raise ValueError(f"getTmuxConnection: Passed value was not Session or "
                         f"Tab but {stab.__class__.__name__}")
    connection = session.connection
    tid = await session.async_run_tmux_command("display-message -p '#h@#H@#S'")
    tmuxes = await iterm2.async_get_tmux_connections(connection)
    for t in tmuxes:
        x_tid = await t.async_send_command("display-message -p '#h@#H@#S'")
        if x_tid == tid:
            tmux = t
            break
    await session.async_set_variable("user.tmux_connection_id", tmux.connection_id)
    return tmux


class TmuxVals():
    def __init__(self, host=None, host_short=None, pane_id=None,
                 pane_index=None, pane_path=None, pane_title=None,
                 session_name=None, window_id=None,
                 window_index=None, window_name=None):
        self.host = host
        self.host_short = host_short

        self.pane_id = pane_id
        self.pane_index = pane_index
        self.pane_path = pane_path
        self.pane_title = pane_title

        self.session_name = session_name

        self.window_id = window_id
        self.window_index = window_index
        self.window_name = window_name


    @classmethod
    async def async_getTmuxIDsFromSession(cls, session):
        ids = ["#H", "#h", "#D", "#P", "#{pane_path}", "#{pane_title}", "#S",
               "#{window_index}", "#I", "#W"]
        sep = "\t"
        message = f"display-message -p '{sep.join(ids)}'"
        vals = await session.async_run_tmux_command(message)
        array = vals.split(sep)
        print(vals)
        tvals = TmuxVals(host=array[0],
                         host_short=array[1],
                         pane_id=array[2],
                         pane_index=array[3],
                         pane_path=array[4],
                         pane_title=array[5],
                         session_name=array[6],
                         window_id=array[7],
                         window_index=array[8],
                         window_name=array[9]
                         )
        return tvals


async def main(connection):
    # Your code goes here. Here's a bit of example code that adds a tab to the current window:
    app = await iterm2.async_get_app(connection)

    window = app.current_window
    tab = window.current_tab
    print(tab.tmux_window_id)
    if tab.tmux_window_id == -1:
        print("Not a TMUX window")
    else:
        session = tab.current_session
        sess_vals = await TmuxVals.async_getTmuxIDsFromSession(session)
        tmux_x = await async_getTmuxConnection(tab)
        new_tab = await window.async_create_tmux_tab(tmux_x)
        new_session = new_tab.current_session
        new_sess_vals = await TmuxVals.async_getTmuxIDsFromSession(new_session)
        tmux_message = f"swap-pane -s {sess_vals.pane_id} -t {new_sess_vals.pane_id}"
        print(f"Sending TMUX message: {tmux_message}")
        print(await tmux_x.async_send_command(tmux_message))

iterm2.run_until_complete(main)