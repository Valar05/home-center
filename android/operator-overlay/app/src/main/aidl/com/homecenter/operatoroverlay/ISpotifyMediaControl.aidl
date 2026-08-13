package com.homecenter.operatoroverlay;

interface ISpotifyMediaControl {
    String probe();
    String status();
    String execute(String action, String argument);
    void destroy() = 16777114;
}
