import asyncio
import time
import random
import socket
import json

class RaftState:
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"

class RaftConsensus:
    def __init__(self, bee_id):
        self.bee_id = bee_id
        self.state = RaftState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.leader_id = None
        
        self.shadow_state = {}
        self.last_heartbeat = time.time()
        
        # Random election timeout between 150-300ms (scaled to seconds for python)
        self.election_timeout = random.uniform(0.150, 0.300)
        
    def reset_election_timer(self):
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(0.150, 0.300)

    def process_append_entries(self, payload):
        term = payload['term']
        leader_id = payload['leaderId']
        
        if term >= self.current_term:
            self.state = RaftState.FOLLOWER
            self.current_term = term
            self.leader_id = leader_id
            self.reset_election_timer()
            
            # Replicate State
            self.shadow_state = payload['hiveState']
            # print(f"[HA] Prince Synced State. Term: {term}")
            return True
            
        return False

    async def run_election_loop(self, broadcast_vote_request_fn, promote_fn):
        """
        Monitors heartbeat. If timeout, starts election.
        broadcast_vote_request_fn: async function to send REQUEST_VOTE to peers
        promote_fn: async function to become Leader
        """
        while True:
            await asyncio.sleep(0.05) # Check frequently
            
            if self.state == RaftState.LEADER:
                continue

            # Check for Timeout
            if time.time() - self.last_heartbeat > self.election_timeout:
                await self.start_election(broadcast_vote_request_fn, promote_fn)

    async def start_election(self, broadcast_vote_request_fn, promote_fn):
        print(f"[HA] Queen Heartbeat Lost! Starting Election (Term {self.current_term + 1})")
        
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.bee_id
        self.votes_received = 1 # Vote for self
        self.reset_election_timer()
        
        # In a real P2P mesh, we'd broadcast to all known peers (from shadow_state)
        # For Phase 1.2, since we are simulating "Taking Over", if we assume we are the only eligible Prince
        # or we just "win" the simulation:
        
        # Simulating winning immediately for the POC if connected peers > 0
        # In full mesh we need to wait for VOTE_ACKs
        
        # Mocking a "Win" for single-Prince failover scenario
        # Real logic:
        # await broadcast_vote_request_fn()
        # if self.votes_received > majority:
        #    self.become_leader(promote_fn)
        
        # For this simulation Step:
        await self.become_leader(promote_fn)

    async def become_leader(self, promote_fn):
        if self.state != RaftState.CANDIDATE:
            return
            
        self.state = RaftState.LEADER
        self.leader_id = self.bee_id
        print(f"[HA] Won Election! Term {self.current_term}. I am the Captain now.")
        await promote_fn()

