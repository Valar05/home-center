package com.homecenter.operatoroverlay;

interface ISpotifyMediaControl {
    String probe() = 1;
    String status() = 2;
    String execute(String action, String argument) = 3;
    void destroy() = 16777114;
}