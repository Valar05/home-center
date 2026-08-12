'use strict';
const {onRequest} = require('firebase-functions/v2/https');
const admin = require('firebase-admin');
const {createVeniceRadioHandler} = require('./venice_radio_api');
admin.initializeApp();
exports.veniceRadioApi = onRequest({timeoutSeconds: 120, memory: '512MiB'}, createVeniceRadioHandler({admin}));
