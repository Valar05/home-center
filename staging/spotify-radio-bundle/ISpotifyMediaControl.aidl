package com.homecenter.operatoroverlay;

interface ISpotifyMediaControl {
    String probe(String requestId);
    String status(String requestId);
    String execute(String requestId, String action, String argument);
    void destroy();
}
