import { Message } from '../types';

export const defaultMessages: Message[] = [
  // Connection messages
  {
    id: 'msg-init',
    type: 'init',
    name: 'Init',
    description: 'Initializes a connection between nodes',
    category: 'connection',
    payload: {
      globalfeatures: '0x',
      localfeatures: '0x2082'
    }
  },
  {
    id: 'msg-error',
    type: 'error',
    name: 'Error',
    description: 'Reports an error to the connected peer',
    category: 'connection',
    payload: {
      channel_id: '0x0000000000000000000000000000000000000000000000000000000000000000',
      data: 'Connection error'
    }
  },
  {
    id: 'msg-warning',
    type: 'warning',
    name: 'Warning',
    description: 'Reports a warning to the connected peer',
    category: 'connection',
    payload: {
      channel_id: '0x0000000000000000000000000000000000000000000000000000000000000000',
      data: 'Connection warning'
    }
  },
  {
    id: 'msg-ping',
    type: 'ping',
    name: 'Ping',
    description: 'Ping message to check liveness',
    category: 'connection',
    payload: {
      num_pong_bytes: 1,
      byteslen: 1
    }
  },
  {
    id: 'msg-pong',
    type: 'pong',
    name: 'Pong',
    description: 'Pong response to a ping',
    category: 'connection',
    payload: {
      byteslen: 1
    }
  },
  
  // Channel messages
  {
    id: 'msg-open-channel',
    type: 'open_channel',
    name: 'Open Channel',
    description: 'Request to open a new payment channel',
    category: 'channel',
    payload: {
      chain_hash: '0x6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000',
      temporary_channel_id: '0x0000000000000000000000000000000000000000000000000000000000000000',
      funding_satoshis: 100000,
      push_msat: 0,
      dust_limit_satoshis: 546,
      max_htlc_value_in_flight_msat: 100000000,
      channel_reserve_satoshis: 1000,
      htlc_minimum_msat: 0,
      feerate_per_kw: 253,
      to_self_delay: 144,
      max_accepted_htlcs: 483,
      funding_pubkey: '0x023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb',
      revocation_basepoint: '0x0212a140cd0c6539d07cd08dfe09984dec3251ea808b892efeac3ede9402bf2b19',
      payment_basepoint: '0x0292df73e0d6647aa1e2f30059902142bc357da7f1e3241906d4e5e7cbd36d7db9',
      delayed_payment_basepoint: '0x0392e8bee4d50c5eb98e3aeaf6749b5493becdc7f6bfd607d27f20f7b268bb48a9',
      htlc_basepoint: '0x0391b6348b50c1740f4def4013553895ed20da97c5b036701aee9e922a5b5c31d4',
      first_per_commitment_point: '0x02466d7fcae563e5cb09a0d1870bb580344804617879a14949cf22285f1bae3f27',
      channel_flags: 1
    }
  },
  {
    id: 'msg-accept-channel',
    type: 'accept_channel',
    name: 'Accept Channel',
    description: 'Accept a channel opening request',
    category: 'channel',
    payload: {
      temporary_channel_id: '0x0000000000000000000000000000000000000000000000000000000000000000',
      dust_limit_satoshis: 546,
      max_htlc_value_in_flight_msat: 100000000,
      channel_reserve_satoshis: 1000,
      htlc_minimum_msat: 0,
      minimum_depth: 3,
      to_self_delay: 144,
      max_accepted_htlcs: 483,
      funding_pubkey: '0x023da092f6980e58d2c037173180e9a465476026ee50f96695963e8efe436f54eb',
      revocation_basepoint: '0x0212a140cd0c6539d07cd08dfe09984dec3251ea808b892efeac3ede9402bf2b19',
      payment_basepoint: '0x0292df73e0d6647aa1e2f30059902142bc357da7f1e3241906d4e5e7cbd36d7db9',
      delayed_payment_basepoint: '0x0392e8bee4d50c5eb98e3aeaf6749b5493becdc7f6bfd607d27f20f7b268bb48a9',
      htlc_basepoint: '0x0391b6348b50c1740f4def4013553895ed20da97c5b036701aee9e922a5b5c31d4',
      first_per_commitment_point: '0x02466d7fcae563e5cb09a0d1870bb580344804617879a14949cf22285f1bae3f27'
    }
  }
];