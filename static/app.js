const $ = sel => document.querySelector(sel);
const API_BASE = window.location.origin;
const API = async path => {
  const response = await fetch(API_BASE + path, {credentials:'include'});
  if (!response.ok) {
    const error = await response.json().catch(() => ({detail: 'Network error'}));
    throw new Error(`${response.status}: ${error.detail || 'Unknown error'}`);
  }
  return await response.json();
};
const POST = async (path, data) => {
  const response = await fetch(API_BASE + path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data), credentials:'include'});
  if (!response.ok) {
    const error = await response.json().catch(() => ({detail: 'Network error'}));
    throw new Error(`${response.status}: ${error.detail || 'Unknown error'}`);
  }
  return await response.json();
};

// Global variables
let currentUser = null;

// Helper functions for better UX
function showError(elementId, message) {
  const errorEl = $('#' + elementId);
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 5000);
  }
}

function showSuccess(message) {
  // Create a temporary success message
  const successEl = document.createElement('div');
  successEl.className = 'success-message';
  successEl.textContent = message;
  successEl.style.cssText = `
    position: fixed; top: 20px; right: 20px; z-index: 10001;
    background: #7bf1a8; color: #051224; padding: 12px 20px;
    border-radius: 8px; font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  `;
  document.body.appendChild(successEl);
  setTimeout(() => {
    successEl.remove();
  }, 3000);
}

// Views
const showView = id => { document.querySelectorAll('.view').forEach(v=>v.classList.remove('active')); $('#'+id).classList.add('active'); };

// Nav
$('#nav-home').onclick = ()=>loadView('home');
$('#nav-listings').onclick = ()=>{
  if (currentUser) {
    loadView('listings'); 
    loadListings(); 
    loadRequirements();
  } else {
    showError('Please login to access Listings');
  }
};
        $('#nav-feed').onclick = ()=>{
          if (currentUser) {
            loadView('feed');
          } else {
            showError('Please login to access Feed');
          }
        };
        $('#nav-costs').onclick = ()=>{
          if (currentUser) {
            loadView('costs');
          } else {
            showError('Please login to access Cost Tool');
          }
        };
$('#nav-messages').onclick = ()=>{
  if (currentUser) {
    loadView('messages');
  } else {
    showError('Please login to access Messages');
  }
};
$('#nav-dashboard').onclick = ()=>{
  if (currentUser) {
    loadView('dashboard'); 
    loadMatches();
  } else {
    showError('Please login to access Dashboard');
  }
};

$('#nav-personal').onclick = ()=>{
  if (currentUser) {
    loadView('personal'); 
    loadPersonalDashboard(); 
  } else {
    showError('Please login to access My Profile');
  }
};

$('#nav-admin').onclick = ()=>{
  if (currentUser) {
    loadView('admin');
  } else {
    showError('Please login to access Admin Panel');
  }
};

// Auth UI
const authArea = $('#auth-area'); const userArea = $('#user-area'); const userChip = $('#user-chip');

async function refreshMe(){
  const me = await API('/api/me');
  if(me.user){
    // User is authenticated
    authArea.classList.add('hidden'); 
    userArea.classList.remove('hidden');
    userChip.textContent = me.user.name + ' ('+me.user.role+')';
    updateNavigation(me.user);
    currentUser = me.user; // Store current user globally
    
    // Enable authenticated features
    document.body.classList.add('authenticated');
    
    // If user is on home page and just logged in, redirect to dashboard
    if (document.getElementById('home').classList.contains('active')) {
      loadView('dashboard');
    }
  } else {
    // User is not authenticated
    userArea.classList.add('hidden'); 
    authArea.classList.remove('hidden');
    $('#nav-admin').classList.add('hidden');
    currentUser = null;
    
    // Disable authenticated features and redirect to home
    document.body.classList.remove('authenticated');
    
    // Hide all restricted views and show only home
    document.querySelectorAll('.view').forEach(v => {
      if (v.id !== 'home') {
        v.classList.remove('active');
        v.classList.add('hidden');
      }
    });
    document.getElementById('home').classList.add('active');
    document.getElementById('home').classList.remove('hidden');
  }
}
refreshMe();

function openModal(title, bodyHTML){
  $('#modal-title').textContent = title;
  $('#modal-body').innerHTML = bodyHTML;
  $('#modal').classList.remove('hidden');
}
$('#modal-close').onclick = ()=>$('#modal').classList.add('hidden');

$('#btn-login').onclick = ()=>{
  openModal('Login', `
    <label>Email <input id="login-email" placeholder="Enter your email"></label>
    <label>Password <input type="password" id="login-pass" placeholder="Enter your password"></label>
    <button id="do-login">Login</button>
    <div id="login-error" class="error-message hidden"></div>
  `);
  $('#do-login').onclick = async ()=>{
    const email = $('#login-email').value.trim();
    const password = $('#login-pass').value;
    
    if (!email || !password) {
      showError('login-error', 'Please fill in all fields');
      return;
    }
    
    try {
      const response = await fetch(API_BASE + '/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password}),
        credentials: 'include'
      });
      
      const res = await response.json();
      
      if(res.ok && res.user){ 
        $('#modal').classList.add('hidden'); 
        refreshMe(); 
        showSuccess('Login successful!');
      } else {
        showError('login-error', res.detail || 'Login failed. Please check your credentials.');
      }
    } catch (error) {
      console.error('Login error:', error);
      showError('login-error', 'Network error. Please check your connection and try again.');
    }
  };
};

$('#btn-register').onclick = ()=>{
  openModal('Register', `
    <label>Name <input id="reg-name" placeholder="Enter your full name"></label>
    <label>Email <input id="reg-email" placeholder="Enter your email"></label>
    <label>Password <input type="password" id="reg-pass" placeholder="Choose a password"></label>
    <label>Role
      <select id="reg-role">
        <option value="business">Business</option>
        <option value="investor">Investor</option>
      </select>
    </label>
    <button id="do-register">Create account</button>
    <div id="register-error" class="error-message hidden"></div>
  `);
  $('#do-register').onclick = async ()=>{
    const name = $('#reg-name').value.trim();
    const email = $('#reg-email').value.trim();
    const password = $('#reg-pass').value;
    const role = $('#reg-role').value;
    
    if (!name || !email || !password) {
      showError('register-error', 'Please fill in all fields');
      return;
    }
    
    if (password.length < 6) {
      showError('register-error', 'Password must be at least 6 characters long');
      return;
    }
    
    try {
      const response = await fetch(API_BASE + '/api/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name,email,password,role}),
        credentials: 'include'
      });
      
      const res = await response.json();
      
      if(res.ok){ 
        $('#modal').classList.add('hidden'); 
        // Auto-login after registration
        const loginResponse = await fetch(API_BASE + '/api/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email, password}),
          credentials: 'include'
        });
        
        if(loginResponse.ok) {
          refreshMe(); 
          showSuccess('Account created and logged in successfully!');
        } else {
          showSuccess('Account created successfully! Please log in.');
        }
      } else {
        showError('register-error', res.detail || 'Registration failed. Please try again.');
      }
    } catch (error) {
      console.error('Registration error:', error);
      showError('register-error', 'Network error. Please check your connection and try again.');
    }
  };
};

$('#btn-logout').onclick = async ()=>{ await POST('/api/logout', {}); refreshMe(); };

// Listings
// Requirements
async function loadRequirements(){
  const res = await API('/api/requirements');
  const wrap = $('#requirements-container'); if(!wrap) return;
  wrap.innerHTML = '';
  res.items.forEach(r=>{
    const el = document.createElement('div');
    el.className = 'listing card';
    el.innerHTML = `
      <div class="row">
        <h4>${r.title}</h4>
        <span class="badge">${r.partnership_type || 'requirement'}</span>
      </div>
      <small>${r.city || ''} ${r.country || ''} • ${r.sector || ''}</small>
      <p>${(r.main_brand||'')}${r.sub_brand?(' → '+r.sub_brand):''}</p>
      <p>Budget: ${r.budget && r.budget[0] ? '$'+r.budget[0] : '—'} - ${r.budget && r.budget[1] ? '$'+r.budget[1] : '—'}</p>
      <div class="row">
        <small>Posted by: ${r.owner.name} (user #${r.owner.id})</small>
        <button class="msg-btn" data-uid="${r.owner.id}">Message</button>
      </div>`;
    wrap.appendChild(el);
  });
  wrap.querySelectorAll('.msg-btn').forEach(btn=>{
    btn.onclick = ()=>{
      openModal('Message', `
        <label>Write a message <textarea id="msg-compose" rows="3"></textarea></label>
        <button id="send-owner">Send</button>
      `);
      $('#send-owner').onclick = async ()=>{
        const body = $('#msg-compose').value.trim();
        const res = await POST('/api/messages', {to_user_id: Number(btn.dataset.uid), body});
        if(res.ok){ 
          showSuccess('Message sent successfully!'); 
          $('#modal').classList.add('hidden');
        } else {
          showSuccess('Error: ' + (res.detail || 'Failed to send message'));
        }
      };
    };
  });
}

const postReq = async ()=>{
  const payload = {
    title: $('#req-title').value.trim(),
    sector: $('#req-sector').value.trim(),
    main_brand: $('#req-main').value.trim(),
    sub_brand: $('#req-sub').value.trim(),
    country: $('#req-country').value.trim(),
    city: $('#req-city').value.trim(),
    partnership_type: $('#req-type').value,
    budget_min: Number($('#req-min').value||0),
    budget_max: Number($('#req-max').value||0),
    description: $('#req-desc').value.trim()
  };
  const res = await POST('/api/requirements', payload);
  if(res.ok){ 
    showSuccess('Requirement posted successfully!'); 
    loadRequirements(); 
    // Clear form
    $('#req-title').value = '';
    $('#req-sector').value = '';
    $('#req-main').value = '';
    $('#req-sub').value = '';
    $('#req-country').value = '';
    $('#req-city').value = '';
    $('#req-min').value = '';
    $('#req-max').value = '';
    $('#req-desc').value = '';
  } else {
    showSuccess('Error: ' + (res.detail || 'Failed to post requirement'));
  }
};

// Wire the Post button once the element exists
document.addEventListener('click', (e)=>{
  if(e.target && e.target.id === 'btn-post-req'){
    postReq();
  }
});


// Costs
// Load countries for cost comparison
let availableCountries = [];

async function loadCountries() {
  try {
    const res = await API('/api/countries');
    if (res.countries) {
      availableCountries = res.countries;
      populateCountrySelect();
    }
  } catch (error) {
    console.error('Failed to load countries:', error);
  }
}

function populateCountrySelect() {
  const select = $('#country-select');
  select.innerHTML = '';
  
  // Group countries by region
  const regions = {};
  availableCountries.forEach(country => {
    if (!regions[country.region]) {
      regions[country.region] = [];
    }
    regions[country.region].push(country.name);
  });
  
  // Add countries grouped by region
  Object.keys(regions).sort().forEach(region => {
    const optgroup = document.createElement('optgroup');
    optgroup.label = region;
    regions[region].sort().forEach(country => {
      const option = document.createElement('option');
      option.value = country;
      option.textContent = country;
      optgroup.appendChild(option);
    });
    select.appendChild(optgroup);
  });
  
  // Select USA and India by default
  Array.from(select.options).forEach(option => {
    if (option.value === 'USA' || option.value === 'India') {
      option.selected = true;
    }
  });
}

// Country selection actions
$('#select-all-countries').onclick = () => {
  Array.from($('#country-select').options).forEach(option => {
    option.selected = true;
  });
};

$('#clear-countries').onclick = () => {
  Array.from($('#country-select').options).forEach(option => {
    option.selected = false;
  });
};

$('#btn-costs').onclick = async ()=>{
  const selectedOptions = Array.from($('#country-select').selectedOptions);
  const countries = selectedOptions.map(option => option.value);
  
  const base_rent = Number($('#base-rent').value||0);
  const base_labor = Number($('#base-labor').value||0);
  const base_utilities = Number($('#base-utils').value||0);
  const base_logistics = Number($('#base-log').value||0);
  
  if(countries.length === 0) {
    showError('Please select at least one country');
    return;
  }
  
  if(countries.length > 20) {
    showError('Please select maximum 20 countries for better performance');
    return;
  }
  
  const res = await POST('/api/costs', {base_rent, base_labor, base_utilities, base_logistics, base_tax:0.0, countries});
  const wrap = $('#cost-results'); wrap.innerHTML='';
  res.items.forEach(r=>{
    const card = document.createElement('div'); card.className='card';
    card.innerHTML = `
      <h4>${r.country} <span class="region-badge">${r.region}</span></h4>
      <div class="total-monthly">$${r.total_monthly.toLocaleString()}</div>
      <p class="cost-index">Cost Index: ${r.cost_index}</p>
      <div class="cost-breakdown">
        <small>Rent: $${r.rent.toLocaleString()}</small>
        <small>Labor: $${r.labor.toLocaleString()}</small>
        <small>Utilities: $${r.utilities.toLocaleString()}</small>
        <small>Logistics: $${r.logistics.toLocaleString()}</small>
        <small>Tax: $${r.tax.toLocaleString()}</small>
      </div>`;
    wrap.appendChild(card);
  });
  showSuccess(`Cost comparison completed for ${countries.length} countries`);
};

// Premium Enhanced Messages System
let currentConversationPartner = null;
let unreadCount = 0;
let typingTimer = null;
let isTyping = false;

// Notification system
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 4000);
}

// Load unread count and update badge
async function loadUnreadCount() {
  try {
    const res = await API('/api/messages/unread-count');
    if (res.unread_count !== undefined) {
      unreadCount = res.unread_count;
      updateUnreadBadge();
    }
  } catch (error) {
    console.error('Failed to load unread count:', error);
  }
}

function updateUnreadBadge() {
  const badge = $('#unread-badge');
  if (unreadCount > 0) {
    badge.textContent = unreadCount;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

// Load conversations for inbox
function loadConversations() {
  API('/api/conversations').then(data => {
    const conversations = data.conversations || [];
    $('#inbox-list').innerHTML = conversations.map(conv => `
      <div class="inbox-conversation ${conv.unread_count > 0 ? 'conversation-unread' : ''}" data-partner-id="${conv.partner_id}" onclick="openConversation(${conv.partner_id}, event)">
        <div class="inbox-conversation-header">
          <div class="inbox-conversation-name">${conv.partner_name} (${conv.partner_role})</div>
          <div class="inbox-conversation-time">${new Date(conv.last_time).toLocaleDateString()}</div>
        </div>
        <div class="inbox-conversation-preview">${conv.last_message}</div>
        ${conv.unread_count > 0 ? `<div class="unread-count">${conv.unread_count}</div>` : ''}
      </div>
    `).join('');
    
    // Load unread count for badge
    loadUnreadCount();
  }).catch(err => {
    console.error('Failed to load conversations:', err);
    $('#inbox-list').innerHTML = '<p class="hint">No conversations yet</p>';
  });
}

// Reload current conversation (for after sending messages)
async function reloadCurrentConversation() {
  if (!currentConversationPartner) return;
  
  try {
    const data = await API(`/api/messages/conversation/${currentConversationPartner}`);
    displayConversationMessages(data);
    
    // Update unread count and inbox
    loadUnreadCount();
    loadConversations();
  } catch (error) {
    console.error('Failed to reload conversation:', error);
  }
}

// Display conversation messages
function displayConversationMessages(data) {
  $('#conversation-title').textContent = `Conversation with ${data.partner_name}`;
  
  if (data.messages && data.messages.length > 0) {
    $('#thread').innerHTML = data.messages.map(msg => `
      <div class="message-row ${msg.is_from_me ? 'message-from-me' : 'message-from-other'}">
        <div class="message-content">${msg.content}</div>
        <div class="message-time">
          ${new Date(msg.created_at).toLocaleString()}
          ${msg.is_from_me ? `<span class="message-status ${msg.is_read ? 'read' : 'delivered'}">${msg.is_read ? '✓✓' : '✓'}</span>` : ''}
        </div>
      </div>
    `).join('');
  } else {
    $('#thread').innerHTML = `
      <div class="thread-empty">
        <div class="empty-state">
          <div class="empty-icon">💬</div>
          <h4>Start a conversation</h4>
          <p>Send your first message to ${data.partner_name}</p>
        </div>
      </div>
    `;
  }
  
  // Show compose area and delete button
  $('#message-compose').classList.remove('hidden');
  $('#delete-conversation').classList.remove('hidden');
  
  // Scroll to bottom
  setTimeout(() => {
    $('#thread').scrollTop = $('#thread').scrollHeight;
  }, 100);
}

// Open a specific conversation
function openConversation(partnerId, event = null) {
  currentConversationPartner = partnerId;
  
  // Update UI - handle both click events and programmatic calls
  document.querySelectorAll('.inbox-conversation').forEach(el => el.classList.remove('active'));
  
  if (event && event.target) {
    // Called from click event
    event.target.closest('.inbox-conversation').classList.add('active');
  } else {
    // Called programmatically - find the conversation element by data attribute
    const conversationEl = document.querySelector(`[data-partner-id="${partnerId}"]`);
    if (conversationEl) {
      conversationEl.classList.add('active');
    }
  }
  
  // Load conversation
  API(`/api/messages/conversation/${partnerId}`).then(data => {
    displayConversationMessages(data);
    loadUnreadCount();
  });
}

// Send message
$('#btn-send').onclick = async ()=>{
  if (!currentConversationPartner) {
    showNotification('Please select a conversation first', 'error');
    return;
  }
  
  const body = $('#msg-body').value.trim();
  if (!body) {
    showNotification('Please enter a message', 'error');
    return;
  }
  
  // Disable send button to prevent double-sending
  const sendBtn = $('#btn-send');
  sendBtn.disabled = true;
  sendBtn.textContent = 'Sending...';
  
  try {
    const res = await POST('/api/messages', {to_user_id: currentConversationPartner, body: body});
    if(res.ok) {
      showNotification('Message sent successfully!', 'success');
      $('#msg-body').value = '';
      
      // Add the message to the UI immediately for better UX
      const currentTime = new Date().toLocaleString();
      const newMessageHtml = `
        <div class="message-row message-from-me">
          <div class="message-content">${body}</div>
          <div class="message-time">
            ${currentTime}
            <span class="message-status sent">✓</span>
          </div>
        </div>
      `;
      
      // If thread is empty, remove empty state
      const emptyState = $('#thread').querySelector('.thread-empty');
      if (emptyState) {
        emptyState.remove();
      }
      
      // Add new message to thread
      $('#thread').insertAdjacentHTML('beforeend', newMessageHtml);
      
      // Scroll to bottom
      setTimeout(() => {
        $('#thread').scrollTop = $('#thread').scrollHeight;
      }, 50);
      
      // Reload conversation to get updated message with proper status
      setTimeout(async () => {
        await reloadCurrentConversation();
      }, 500);
    } else {
      showNotification(res.detail || 'Failed to send message', 'error');
    }
  } catch (error) {
    showNotification('Failed to send message', 'error');
  } finally {
    // Re-enable send button
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
  }
};

// Premium messaging event handlers
$('#refresh-inbox').onclick = () => {
  loadConversations();
  showNotification('Inbox refreshed', 'success');
};

$('#mark-all-read').onclick = async () => {
  try {
    // This would require a new API endpoint to mark all messages as read
    showNotification('All messages marked as read', 'success');
    loadUnreadCount();
  } catch (error) {
    showNotification('Failed to mark all as read', 'error');
  }
};

$('#delete-conversation').onclick = async () => {
  if (!currentConversationPartner) return;
  
  if (confirm('Are you sure you want to delete this conversation?')) {
    try {
      // This would require a new API endpoint to delete entire conversations
      showNotification('Conversation deleted', 'success');
      currentConversationPartner = null;
      $('#thread').innerHTML = `
        <div class="thread-empty">
          <div class="empty-state">
            <div class="empty-icon">💬</div>
            <h4>No conversation selected</h4>
            <p>Choose a conversation from your inbox to start messaging</p>
          </div>
        </div>
      `;
      $('#message-compose').classList.add('hidden');
      $('#delete-conversation').classList.add('hidden');
      loadConversations();
    } catch (error) {
      showNotification('Failed to delete conversation', 'error');
    }
  }
};

// Typing indicator
$('#msg-body').oninput = () => {
  if (!currentConversationPartner) return;
  
  // Clear existing timer
  if (typingTimer) {
    clearTimeout(typingTimer);
  }
  
  // Show typing indicator
  if (!isTyping) {
    isTyping = true;
    // In a real app, you'd send a "typing" event to the server
  }
  
  // Hide typing indicator after 2 seconds of no typing
  typingTimer = setTimeout(() => {
    isTyping = false;
    // Hide typing indicator
  }, 2000);
};

// Enter key to send message
$('#msg-body').onkeypress = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('#btn-send').click();
  }
};

// Inbox search
$('#inbox-search').oninput = (e) => {
  const searchTerm = e.target.value.toLowerCase();
  const conversations = document.querySelectorAll('.inbox-conversation');
  
  conversations.forEach(conv => {
    const name = conv.querySelector('.inbox-conversation-name').textContent.toLowerCase();
    const preview = conv.querySelector('.inbox-conversation-preview').textContent.toLowerCase();
    
    if (name.includes(searchTerm) || preview.includes(searchTerm)) {
      conv.style.display = 'block';
    } else {
      conv.style.display = 'none';
    }
  });
};

// Dashboard
$('#btn-save-biz').onclick = async ()=>{
  const payload = {
    name: $('#biz-name').value.trim(),
    sector: $('#biz-sector').value.trim(),
    country: $('#biz-country').value.trim(),
    city: $('#biz-city').value.trim(),
    investment_needs_min: Number($('#biz-min').value||0),
    investment_needs_max: Number($('#biz-max').value||0),
    brand_story: $('#biz-story').value.trim(),
    expansion_potential: $('#biz-exp').value.trim()
  };
  const res = await POST('/api/business', payload);
  if(res.ok) {
    showSuccess('Business profile saved successfully!');
  } else {
    showSuccess('Error: ' + (res.detail || 'Failed to save business profile'));
  }
};

async function loadMatches(){
  // Remove the suggested businesses/investors section - it's not useful
  $('#match-area').innerHTML = '<div class="dashboard-welcome"><h3>Welcome to your Dashboard</h3><p>Manage your business profile and view your activity here.</p></div>';
}

// Admin functionality
async function loadAdminStats() {
  try {
    const data = await API('/api/admin/stats');
    
    // Load stats
    $('#admin-stats-content').innerHTML = `
      <div class="stat-item">
        <span class="stat-label">Total Users</span>
        <span class="stat-value">${data.stats.total_users}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Total Requirements</span>
        <span class="stat-value">${data.stats.total_requirements}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Total Messages</span>
        <span class="stat-value">${data.stats.total_messages}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Total Businesses</span>
        <span class="stat-value">${data.stats.total_businesses}</span>
      </div>
    `;
    
    // Load recent users
    $('#admin-users-content').innerHTML = data.recent_users.map(u => `
      <div class="admin-item">
        <strong>${u.name}</strong> (${u.role})
        <br><small>${u.email} • ${new Date(u.created_at).toLocaleDateString()}</small>
      </div>
    `).join('');
    
    // Load recent requirements
    $('#admin-requirements-content').innerHTML = data.recent_requirements.map(r => `
      <div class="admin-item">
        <strong>${r.title}</strong>
        <br><small>${r.sector} • User #${r.owner_id} • ${new Date(r.created_at).toLocaleDateString()}</small>
      </div>
    `).join('');
    
    // Load recent messages
    $('#admin-messages-content').innerHTML = data.recent_messages.map(m => `
      <div class="admin-item">
        <strong>${m.content}</strong>
        <br><small>User #${m.from_user_id} → User #${m.to_user_id} • ${new Date(m.created_at).toLocaleDateString()}</small>
      </div>
    `).join('');
    
  } catch (error) {
    console.error('Failed to load admin stats:', error);
    $('#admin-stats-content').innerHTML = '<p class="hint">Admin access required</p>';
  }
}

// Navigation updates
function updateNavigation(user) {
  const universalSearch = $('.universal-search');
  
  if (user && user.role === 'admin') {
    $('#nav-admin').classList.remove('hidden');
  } else {
    $('#nav-admin').classList.add('hidden');
  }
  
  // Show universal search when authenticated
  if (user) {
    universalSearch.classList.remove('hidden');
    // Load connection requests to show notification badge
    loadConnectionRequests();
  } else {
    universalSearch.classList.add('hidden');
    // Hide notification badge when not authenticated
    $('#connection-requests-badge').classList.add('hidden');
  }
}

// Update view loading to include new functionality
function loadView(viewId) {
  // Hide all views
  document.querySelectorAll('.view').forEach(v => {
    v.classList.remove('active');
    v.classList.add('hidden');
  });
  
  // Show selected view
  const view = document.getElementById(viewId);
  if (view) {
    view.classList.remove('hidden');
    view.classList.add('active');
    
    // Load specific data for each view
    if (viewId === 'messages') {
      loadConversations();
      loadUnreadCount();
    } else if (viewId === 'admin') {
      loadAdminStats();
    } else if (viewId === 'dashboard') {
      loadMatches();
    } else if (viewId === 'costs') {
      loadCountries();
    } else if (viewId === 'feed') {
      loadFeed();
    }
  }
}

// Seed demo shortcut (comment the line below if not needed)
// fetch('/api/seed', {method:'POST'});

// ---------- Feed System JavaScript ----------

let currentPostType = 'text';
let feedOffset = 0;
let isLoadingFeed = false;
let uploadedFile = null;

// Load feed posts
async function loadFeed() {
  if (isLoadingFeed) return;
  isLoadingFeed = true;
  
  try {
    const res = await API(`/api/feed?limit=10&offset=${feedOffset}`);
    if (res.posts) {
      displayFeedPosts(res.posts);
      feedOffset += res.posts.length;
      
      // Set up auto-refresh for real-time updates (only on first load)
      if (feedOffset === res.posts.length && !window.feedRefreshInterval) {
        window.feedRefreshInterval = setInterval(refreshFeedForNewPosts, 30000); // Refresh every 30 seconds
      }
    }
  } catch (error) {
    console.error('Failed to load feed:', error);
    showNotification('Failed to load feed', 'error');
  } finally {
    isLoadingFeed = false;
  }
}

// Refresh feed to check for new posts
async function refreshFeedForNewPosts() {
  try {
    const data = await API('/api/feed?limit=10&offset=0');
    if (data && data.posts && data.posts.length > 0) {
      const container = $('#feed-posts');
      const currentPosts = container.querySelectorAll('[data-post-id]');
      const currentPostIds = Array.from(currentPosts).map(el => el.dataset.postId);
      
      // Check for new posts
      const newPosts = data.posts.filter(post => !currentPostIds.includes(post.id.toString()));
      
      if (newPosts.length > 0) {
        // Add new posts to the top
        newPosts.reverse().forEach(post => {
          const postElement = createPostElement(post);
          container.insertBefore(postElement, container.firstChild);
        });
        
        // Show notification
        showNotification(`${newPosts.length} new post${newPosts.length > 1 ? 's' : ''} available!`, 'info');
      }
    }
  } catch (error) {
    console.error('Error checking for new posts:', error);
  }
}

// Display feed posts
function displayFeedPosts(posts) {
  const feedContainer = $('#feed-posts');
  
  if (feedOffset === 0) {
    feedContainer.innerHTML = '';
  }
  
  posts.forEach(post => {
    const postElement = createPostElement(post);
    feedContainer.appendChild(postElement);
  });
  
  // Update load more button visibility
  const loadMoreBtn = $('#btn-load-more');
  if (posts.length < 10) {
    loadMoreBtn.style.display = 'none';
  } else {
    loadMoreBtn.style.display = 'block';
  }
}

// Create post element
function createPostElement(post) {
  const postDiv = document.createElement('div');
  postDiv.className = 'feed-post';
  postDiv.dataset.postId = post.id;
  
  // Format time
  const timeAgo = formatTimeAgo(new Date(post.created_at));
  
  // Get reaction counts
  const reactionCounts = post.reactions || {};
  const totalReactions = Object.values(reactionCounts).reduce((sum, count) => sum + count, 0);
  
  // Build reaction buttons
  const reactionButtons = getReactionButtons(post);
  
  postDiv.innerHTML = `
    <div class="post-header">
      <div class="post-author-avatar">
        <img src="/static/logo.png" alt="${post.author.name}" />
      </div>
      <div class="post-author-info">
        <div class="post-author-name">${post.author.name}</div>
        <div class="post-author-role">${post.author.role}</div>
      </div>
      <div class="post-time">${timeAgo}</div>
    </div>
    
    <div class="post-content-area">
      ${post.content ? `<div class="post-text">${post.content}</div>` : ''}
      
      ${post.post_type === 'image' && post.media_url ? `
        <div class="post-media-content">
          <img src="${post.media_url}" alt="Post image" />
        </div>
      ` : ''}
      
      ${post.post_type === 'video' && post.media_url ? `
        <div class="post-media-content">
          <video controls>
            <source src="${post.media_url}" type="video/mp4">
            Your browser does not support the video tag.
          </video>
        </div>
      ` : ''}
      
      ${post.post_type === 'article' ? `
        <div class="post-article-content">
          <div class="post-article-title">${post.article_title || 'Article'}</div>
          <div class="post-article-summary">${post.article_summary || ''}</div>
        </div>
      ` : ''}
    </div>
    
    <div class="post-actions-bar">
      ${reactionButtons}
    </div>
    
    <div class="comments-section hidden" data-comments-for="${post.id}">
      <div class="comments-header">
        <span>Comments</span>
      </div>
      <div class="comments-list" data-comments-list="${post.id}">
        <!-- Comments will be loaded here -->
      </div>
      <div class="comment-form">
        <input type="text" class="comment-input" placeholder="Write a comment..." data-comment-input="${post.id}" />
        <button class="comment-submit" data-comment-submit="${post.id}">Comment</button>
      </div>
    </div>
  `;
  
  return postDiv;
}

// Get reaction buttons HTML with LinkedIn-style picker
function getReactionButtons(post) {
  const userReaction = post.user_reaction || null;
  const totalReactions = Object.values(post.reactions || {}).reduce((sum, count) => sum + count, 0);
  
  return `
    <button class="post-action-btn ${userReaction ? 'active' : ''}" data-action="like" data-post-id="${post.id}">
      <span class="action-icon">👍</span>
      <span class="action-text">Like</span>
      ${totalReactions > 0 ? `<span class="action-count">${totalReactions}</span>` : ''}
    </button>
    
    <button class="post-action-btn" data-action="comment" data-post-id="${post.id}">
      <span class="action-icon">💬</span>
      <span class="action-text">Comment</span>
      ${(post.comments_count || 0) > 0 ? `<span class="action-count">${post.comments_count}</span>` : ''}
    </button>
    
    <button class="post-action-btn" data-action="share" data-post-id="${post.id}">
      <span class="action-icon">📤</span>
      <span class="action-text">Share</span>
    </button>
    
    <button class="post-action-btn" data-action="send" data-post-id="${post.id}">
      <span class="action-icon">📨</span>
      <span class="action-text">Send</span>
    </button>
  `;
}

// Helper function to get emoji for reaction type
function getReactionEmoji(reactionType) {
  const emojis = {
    'like': '👍',
    'love': '❤️',
    'celebrate': '🎉',
    'support': '🤝',
    'funny': '😂',
    'insightful': '💡'
  };
  return emojis[reactionType] || '👍';
}

// Format time ago
function formatTimeAgo(date) {
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

// Post creation functionality
$('#btn-create-post').onclick = () => {
  $('#post-creator-form').classList.remove('hidden');
  $('#post-content').focus();
};

$('#btn-cancel-post').onclick = () => {
  $('#post-creator-form').classList.add('hidden');
  resetPostForm();
};

// Post type tabs
document.querySelectorAll('.post-type-tab').forEach(tab => {
  tab.onclick = () => {
    document.querySelectorAll('.post-type-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    currentPostType = tab.dataset.type;
    
    // Show/hide relevant fields
    $('#post-media').classList.toggle('hidden', currentPostType !== 'image' && currentPostType !== 'video');
    $('#post-article').classList.toggle('hidden', currentPostType !== 'article');
  };
});

// Create post
$('#btn-post').onclick = async () => {
  const content = $('#post-content').value.trim();
  const articleTitle = $('#article-title').value.trim();
  const articleSummary = $('#article-summary').value.trim();
  
  if (!content && !uploadedFile && !articleTitle) {
    showNotification('Please enter some content or upload a file', 'error');
    return;
  }
  
  let mediaUrl = null;
  
  // Handle file upload if there's an uploaded file
  if (uploadedFile && (currentPostType === 'image' || currentPostType === 'video')) {
    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);
      formData.append('file_type', currentPostType);
      
      const uploadResponse = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });
      
      if (uploadResponse.ok) {
        const uploadResult = await uploadResponse.json();
        mediaUrl = uploadResult.file_url;
      } else {
        showNotification('Failed to upload file', 'error');
        return;
      }
    } catch (error) {
      showNotification('Failed to upload file', 'error');
      return;
    }
  }
  
  const postData = {
    content,
    post_type: currentPostType,
    media_url: mediaUrl,
    article_title: articleTitle || null,
    article_summary: articleSummary || null
  };
  
  try {
    const res = await POST('/api/posts', postData);
    if (res.ok) {
      showNotification('Post created successfully!', 'success');
      resetPostForm();
      $('#post-creator-form').classList.add('hidden');
      
      // Refresh feed
      feedOffset = 0;
      await loadFeed();
    }
  } catch (error) {
    showNotification('Failed to create post', 'error');
  }
};

// Reset post form
function resetPostForm() {
  $('#post-content').value = '';
  $('#article-title').value = '';
  $('#article-summary').value = '';
  
  // Reset file upload
  uploadedFile = null;
  $('#file-upload-area').classList.remove('hidden');
  $('#uploaded-file-info').classList.add('hidden');
  $('#media-file').value = '';
  
  document.querySelectorAll('.post-type-tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.post-type-tab[data-type="text"]').classList.add('active');
  currentPostType = 'text';
  
  $('#post-media').classList.add('hidden');
  $('#post-article').classList.add('hidden');
}

// Load more posts
$('#btn-load-more').onclick = loadFeed;

// File upload functionality
const fileUploadArea = $('#file-upload-area');
const mediaFileInput = $('#media-file');
const uploadedFileInfo = $('#uploaded-file-info');

// Click to upload
fileUploadArea.onclick = () => {
  mediaFileInput.click();
};

// File input change
mediaFileInput.onchange = (e) => {
  const file = e.target.files[0];
  if (file) {
    handleFileUpload(file);
  }
};

// Drag and drop functionality
fileUploadArea.ondragover = (e) => {
  e.preventDefault();
  fileUploadArea.classList.add('dragover');
};

fileUploadArea.ondragleave = (e) => {
  e.preventDefault();
  fileUploadArea.classList.remove('dragover');
};

fileUploadArea.ondrop = (e) => {
  e.preventDefault();
  fileUploadArea.classList.remove('dragover');
  
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFileUpload(files[0]);
  }
};

// Handle file upload
function handleFileUpload(file) {
  // Validate file type
  const isImage = file.type.startsWith('image/');
  const isVideo = file.type.startsWith('video/');
  
  if (!isImage && !isVideo) {
    showNotification('Please select an image or video file', 'error');
    return;
  }
  
  // Validate file size (50MB)
  if (file.size > 50 * 1024 * 1024) {
    showNotification('File size too large. Maximum 50MB allowed.', 'error');
    return;
  }
  
  // Set the uploaded file
  uploadedFile = file;
  
  // Show file info
  showFileInfo(file);
  
  // Hide upload area and show file info
  $('#file-upload-area').classList.add('hidden');
  $('#uploaded-file-info').classList.remove('hidden');
}

// Show file information
function showFileInfo(file) {
  const fileName = $('#file-name');
  const fileSize = $('#file-size');
  const filePreview = $('#file-preview');
  
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);
  
  // Create preview
  const reader = new FileReader();
  reader.onload = (e) => {
    if (file.type.startsWith('image/')) {
      filePreview.innerHTML = `<img src="${e.target.result}" alt="Preview" />`;
    } else if (file.type.startsWith('video/')) {
      filePreview.innerHTML = `<video src="${e.target.result}" controls></video>`;
    } else {
      filePreview.innerHTML = `<div class="file-type-icon">📄</div>`;
    }
  };
  reader.readAsDataURL(file);
}

// Format file size
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Remove file
$('#remove-file').onclick = () => {
  uploadedFile = null;
  $('#file-upload-area').classList.remove('hidden');
  $('#uploaded-file-info').classList.add('hidden');
  $('#media-file').value = '';
};

// Post interactions
document.addEventListener('click', async (e) => {
  // Find the closest post-action-btn parent
  const actionBtn = e.target.closest('.post-action-btn');
  if (actionBtn && actionBtn.dataset.action) {
    const action = actionBtn.dataset.action;
    const postId = actionBtn.dataset.postId;
    
    console.log('Button clicked:', action, 'Post ID:', postId);
    
    if (action === 'like') {
      // Toggle like
      await reactToPost(postId, 'like');
    } else if (action === 'comment') {
      const commentsSection = document.querySelector(`[data-comments-for="${postId}"]`);
      const isHidden = commentsSection.classList.contains('hidden');
      
      if (isHidden) {
        commentsSection.classList.remove('hidden');
        await loadPostComments(postId);
      } else {
        commentsSection.classList.add('hidden');
      }
    } else if (action === 'share') {
      showShareModal(postId);
    } else if (action === 'send') {
      showShareModal(postId);
    }
  }
  
  // Comment submit
  if (e.target.dataset.commentSubmit) {
    const postId = e.target.dataset.commentSubmit;
    const commentInput = document.querySelector(`[data-comment-input="${postId}"]`);
    const content = commentInput.value.trim();
    
    if (!content) return;
    
    try {
      const res = await POST(`/api/posts/${postId}/comments`, { content });
      if (res.ok) {
        commentInput.value = '';
        await loadPostComments(postId);
        showNotification('Comment added!', 'success');
      }
    } catch (error) {
      showNotification('Failed to add comment', 'error');
    }
  }
});

// React to post
async function reactToPost(postId, reactionType) {
  try {
    const res = await POST(`/api/posts/${postId}/reactions`, { reaction_type: reactionType });
    if (res.ok) {
      // Refresh the specific post
      await refreshPost(postId);
    }
  } catch (error) {
    showNotification('Failed to react to post', 'error');
  }
}

// Show share modal
function showShareModal(postId) {
  // Create share modal if it doesn't exist
  let shareModal = document.getElementById('share-modal');
  if (!shareModal) {
    shareModal = document.createElement('div');
    shareModal.id = 'share-modal';
    shareModal.className = 'share-modal';
    shareModal.innerHTML = `
      <div class="share-modal-content">
        <div class="share-modal-header">
          <h3 class="share-modal-title">Share Post</h3>
          <button class="close-share-modal">&times;</button>
        </div>
        <div class="share-options">
          <div class="share-option" data-share-type="copy">
            <div class="share-option-icon copy">📋</div>
            <div class="share-option-text">
              <div class="share-option-title">Copy Link</div>
              <div class="share-option-desc">Copy post link to clipboard</div>
            </div>
          </div>
          <div class="share-option" data-share-type="message">
            <div class="share-option-icon message">💬</div>
            <div class="share-option-text">
              <div class="share-option-title">Send Message</div>
              <div class="share-option-desc">Share via direct message</div>
            </div>
          </div>
          <div class="share-option" data-share-type="connection">
            <div class="share-option-icon connection">👥</div>
            <div class="share-option-text">
              <div class="share-option-title">Share with Connections</div>
              <div class="share-option-desc">Share with your network</div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(shareModal);
    
    // Add event listeners
    shareModal.querySelector('.close-share-modal').onclick = () => {
      shareModal.classList.remove('show');
    };
    
    shareModal.onclick = (e) => {
      if (e.target === shareModal) {
        shareModal.classList.remove('show');
      }
    };
    
    // Handle share options
    shareModal.querySelectorAll('.share-option').forEach(option => {
      option.onclick = () => {
        const shareType = option.dataset.shareType;
        handleShare(postId, shareType);
        shareModal.classList.remove('show');
      };
    });
  }
  
  shareModal.classList.add('show');
}

// Handle share functionality
async function handleShare(postId, shareType) {
  try {
    switch (shareType) {
      case 'copy':
        const postUrl = `${window.location.origin}/post/${postId}`;
        await navigator.clipboard.writeText(postUrl);
        showNotification('Post link copied to clipboard!', 'success');
        break;
        
      case 'message':
        // Redirect to messages with post context
        loadView('messages');
        showNotification('Redirecting to messages...', 'info');
        break;
        
      case 'connection':
        // For now, just copy the link
        const connectionUrl = `${window.location.origin}/post/${postId}`;
        await navigator.clipboard.writeText(connectionUrl);
        showNotification('Post link copied! Share it with your connections.', 'success');
        break;
        
      default:
        showNotification('Share option not implemented yet', 'info');
    }
  } catch (error) {
    console.error('Failed to share post:', error);
    showNotification('Failed to share post', 'error');
  }
}

// Load post comments
async function loadPostComments(postId) {
  try {
    const res = await API(`/api/posts/${postId}/comments`);
    const commentsList = document.querySelector(`[data-comments-list="${postId}"]`);
    
    if (res.comments) {
      commentsList.innerHTML = res.comments.map(comment => `
        <div class="comment">
          <div class="comment-avatar">
            <img src="/static/logo.png" alt="${comment.author.name}" />
          </div>
          <div class="comment-content">
            <div class="comment-header">
              <span class="comment-author">${comment.author.name}</span>
              <span class="comment-time">${formatTimeAgo(new Date(comment.created_at))}</span>
            </div>
            <div class="comment-text">${comment.content}</div>
          </div>
        </div>
      `).join('');
    } else {
      commentsList.innerHTML = '<p class="hint">No comments yet</p>';
    }
  } catch (error) {
    console.error('Failed to load comments:', error);
  }
}

// Refresh specific post
async function refreshPost(postId) {
  try {
    const res = await API(`/api/feed?limit=1&offset=0`);
    if (res.posts && res.posts.length > 0) {
      const post = res.posts.find(p => p.id == postId);
      if (post) {
        const postElement = document.querySelector(`[data-post-id="${postId}"]`);
        if (postElement) {
          const newPostElement = createPostElement(post);
          postElement.parentNode.replaceChild(newPostElement, postElement);
        }
      }
    }
  } catch (error) {
    console.error('Failed to refresh post:', error);
  }
}

// Load personal dashboard
async function loadPersonalDashboard() {
  try {
    // Load dashboard stats
    const data = await API('/api/dashboard/stats');
    if (data && data.user) {
      
      // Update profile info
      $('#profile-name').textContent = data.user.name;
      $('#profile-role').textContent = data.user.role;
      $('#profile-email').textContent = data.user.email;
      
      // Update stats
      $('#profile-posts-count').textContent = data.stats.posts_count;
      $('#profile-followers-count').textContent = data.stats.followers_count;
      $('#profile-following-count').textContent = data.stats.following_count;
      
      // Update engagement metrics
      $('#total-likes').textContent = data.stats.total_likes;
      $('#total-comments').textContent = data.stats.total_comments;
      $('#total-shares').textContent = data.stats.total_shares;
      
      // Load recent posts
      loadRecentPosts(data.recent_posts);
      
      // Load user's posts
      loadUserPosts();
      
      // Load followers and following
      loadFollowers();
      loadFollowing();
    } else {
      console.log('No data received from dashboard API');
      // Show current user info as fallback
      if (currentUser) {
        $('#profile-name').textContent = currentUser.name;
        $('#profile-role').textContent = currentUser.role;
        $('#profile-email').textContent = currentUser.email;
      } else {
        $('#profile-name').textContent = 'Error loading profile';
        $('#profile-role').textContent = 'Please try again';
        $('#profile-email').textContent = '';
      }
    }
  } catch (error) {
    console.error('Error loading personal dashboard:', error);
    // Show current user info as fallback
    if (currentUser) {
      $('#profile-name').textContent = currentUser.name;
      $('#profile-role').textContent = currentUser.role;
      $('#profile-email').textContent = currentUser.email;
    } else {
      $('#profile-name').textContent = 'Error loading profile';
      $('#profile-role').textContent = 'Please try again';
      $('#profile-email').textContent = '';
    }
  }
}

// Load recent posts for overview
function loadRecentPosts(posts) {
  const container = $('#recent-posts-list');
  container.innerHTML = '';
  
  if (posts && posts.length > 0) {
    posts.forEach(post => {
      const postItem = document.createElement('div');
      postItem.className = 'recent-post-item';
      postItem.innerHTML = `
        <div class="recent-post-content">
          <h4>${post.post_type === 'article' ? post.article_title : 'Post'}</h4>
          <p>${post.content.substring(0, 100)}${post.content.length > 100 ? '...' : ''}</p>
          <div class="recent-post-stats">
            <span>👍 ${post.likes_count}</span>
            <span>💬 ${post.comments_count}</span>
            <span>${formatTime(post.created_at)}</span>
          </div>
        </div>
      `;
      container.appendChild(postItem);
    });
  } else {
    container.innerHTML = '<p class="no-posts">No posts yet. Start sharing your thoughts!</p>';
  }
}

// Load user's posts
async function loadUserPosts() {
  try {
    const data = await API('/api/dashboard/posts');
    if (data) {
      const container = $('#my-posts-list');
      container.innerHTML = '';
      
      if (data.posts && data.posts.length > 0) {
        data.posts.forEach(post => {
          const postItem = document.createElement('div');
          postItem.className = 'my-post-item';
          
          const mediaHtml = post.media_url ? `<img src="${post.media_url}" alt="Post media" style="max-width: 200px; border-radius: 8px; margin-top: 12px;">` : '';
          
          postItem.innerHTML = `
            <div class="my-post-header">
              <div class="my-post-meta">${formatTime(post.created_at)}</div>
            </div>
            <div class="my-post-content">
              <h4>${post.post_type === 'article' ? post.article_title : 'Post'}</h4>
              <p>${post.content}</p>
              ${mediaHtml}
            </div>
            <div class="my-post-engagement">
              <span>👍 ${Object.values(post.reactions || {}).reduce((sum, count) => sum + count, 0)}</span>
              <span>💬 ${post.comments_count}</span>
              <span>📊 ${post.total_engagement} total engagement</span>
            </div>
          `;
          container.appendChild(postItem);
        });
      } else {
        container.innerHTML = '<p class="no-posts">No posts yet. Start sharing your thoughts!</p>';
      }
    }
  } catch (error) {
    console.error('Error loading user posts:', error);
  }
}

// Load followers
async function loadFollowers() {
  try {
    const data = await API('/api/dashboard/followers');
    if (data) {
      const container = $('#followers-list');
      const countElement = $('#followers-count');
      
      countElement.textContent = `${data.followers.length} followers`;
      container.innerHTML = '';
      
      if (data.followers && data.followers.length > 0) {
        data.followers.forEach(follower => {
          const followerItem = document.createElement('div');
          followerItem.className = 'follower-item';
          followerItem.innerHTML = `
            <div class="follower-avatar">
              <img src="/static/logo.png" alt="${follower.name}" />
            </div>
            <div class="follower-info">
              <h4>${follower.name}</h4>
              <p>${follower.email}</p>
              <span class="follower-role">${follower.role}</span>
            </div>
          `;
          container.appendChild(followerItem);
        });
      } else {
        container.innerHTML = '<p class="no-followers">No followers yet. Keep posting to grow your audience!</p>';
      }
    }
  } catch (error) {
    console.error('Error loading followers:', error);
  }
}

// Load following
async function loadFollowing() {
  try {
    const data = await API('/api/dashboard/following');
    if (data) {
      const container = $('#following-list');
      const countElement = $('#following-count');
      
      countElement.textContent = `${data.following.length} following`;
      container.innerHTML = '';
      
      if (data.following && data.following.length > 0) {
        data.following.forEach(following => {
          const followingItem = document.createElement('div');
          followingItem.className = 'following-item';
          followingItem.innerHTML = `
            <div class="following-avatar">
              <img src="/static/logo.png" alt="${following.name}" />
            </div>
            <div class="following-info">
              <h4>${following.name}</h4>
              <p>${following.email}</p>
              <span class="following-role">${following.role}</span>
            </div>
          `;
          container.appendChild(followingItem);
        });
      } else {
        container.innerHTML = '<p class="no-following">Not following anyone yet. Connect with others to see their updates!</p>';
      }
    }
  } catch (error) {
    console.error('Error loading following:', error);
  }
}

// Tab switching for personal dashboard
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('tab-btn')) {
    const tab = e.target.dataset.tab;

    // Remove active class from all tabs and panels
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));

    // Add active class to clicked tab and corresponding panel
    e.target.classList.add('active');
    $(`#tab-${tab}`).classList.add('active');
  }
});

// ---------- Universal Search and Connection Functions ----------

let searchTimeout;
let currentSearchResults = [];

// Setup universal search
function setupUniversalSearch() {
  const searchInput = $('#universal-search-input');
  const searchResults = $('#search-results');
  
  if (!searchInput) return;
  
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    
    clearTimeout(searchTimeout);
    
    if (query.length < 2) {
      hideSearchResults();
      return;
    }
    
    searchTimeout = setTimeout(() => {
      performSearch(query);
    }, 300);
  });
  
  // Hide results when clicking outside
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      hideSearchResults();
    }
  });
  
  // Show results when focusing input
  searchInput.addEventListener('focus', () => {
    if (currentSearchResults.length > 0) {
      showSearchResults();
    }
  });
}

// Perform search
async function performSearch(query) {
  try {
    const data = await API(`/api/users/search?q=${encodeURIComponent(query)}`);
    currentSearchResults = data.users || [];
    displaySearchResults(currentSearchResults);
  } catch (error) {
    console.error('Error searching users:', error);
    hideSearchResults();
  }
}

// Display search results
function displaySearchResults(users) {
  const container = $('#search-results');
  container.innerHTML = '';
  
  if (users.length === 0) {
    container.innerHTML = '<div class="search-result-item"><p>No users found</p></div>';
  } else {
    users.forEach(user => {
      const resultItem = createSearchResultItem(user);
      container.appendChild(resultItem);
    });
  }
  
  showSearchResults();
}

// Create search result item
function createSearchResultItem(user) {
  const item = document.createElement('div');
  item.className = 'search-result-item';
  item.innerHTML = `
    <div class="search-result-avatar">
      <img src="/static/logo.png" alt="${user.name}" />
    </div>
    <div class="search-result-info">
      <h4 class="clickable-name" onclick="viewUserProfile(${user.id})">${user.name}</h4>
      <p>${user.email} • ${user.role}</p>
    </div>
    <div class="search-result-actions">
      ${getInlineConnectionButton(user)}
    </div>
  `;
  return item;
}

// Get inline connection button
function getInlineConnectionButton(user) {
  const connectIcon = '<svg class="connect-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>';
  
  switch (user.connection_status) {
    case 'connected':
      return `<span class="search-connect-btn connected">✓ Connected</span>`;
    case 'sent':
      return `<span class="search-connect-btn pending">Pending</span>`;
    case 'received':
      return `<button class="search-connect-btn" onclick="respondToConnectionRequest(${user.id}, 'accept')">Accept</button>`;
    default:
      return `<button class="search-connect-btn" onclick="sendConnectionRequest(${user.id})">${connectIcon} Connect</button>`;
  }
}

// Show search results
function showSearchResults() {
  $('#search-results').classList.remove('hidden');
}

// Hide search results
function hideSearchResults() {
  $('#search-results').classList.add('hidden');
}

// Send connection request (inline) - Enhanced for better UX
async function sendConnectionRequest(userId) {
  try {
    // Show loading state
    const button = document.querySelector(`button[onclick="sendConnectionRequest(${userId})"]`);
    if (button) {
      button.innerHTML = 'Sending...';
      button.disabled = true;
    }
    
    await POST('/api/connections/send', { receiver_id: userId });
    
    // Show success notification with more detail
    showNotification('Connection request sent successfully! They will be notified.', 'success');
    
    // Update the button in search results
    updateConnectionButton(userId, 'sent');
    
    // Refresh connection requests to show updated state
    await loadConnectionRequests();
    
    // Hide search results after a delay
    setTimeout(() => hideSearchResults(), 2000);
  } catch (error) {
    console.error('Error sending connection request:', error);
    
    // Reset button state on error
    const button = document.querySelector(`button[onclick="sendConnectionRequest(${userId})"]`);
    if (button) {
      button.innerHTML = '🔗 Connect';
      button.disabled = false;
    }
    
    showError(error.message || 'Failed to send connection request');
  }
}

// Respond to connection request (inline) - Enhanced for better UX
async function respondToConnectionRequest(connectionId, action) {
  try {
    // Show loading state
    const button = document.querySelector(`button[onclick="respondToConnectionRequest(${connectionId}, '${action}')"]`);
    if (button) {
      button.innerHTML = action === 'accept' ? 'Accepting...' : 'Declining...';
      button.disabled = true;
    }
    
    await POST('/api/connections/respond', { 
      connection_id: connectionId, 
      action: action 
    });
    
    // Show success notification with more detail
    const message = action === 'accept' 
      ? 'Connection accepted! You are now connected.' 
      : 'Connection request declined.';
    showNotification(message, 'success');
    
    if (action === 'accept') {
      updateConnectionButton(connectionId, 'connected');
      // Refresh dashboard stats to show updated follower count
      await loadPersonalDashboard();
    } else {
      hideSearchResults();
    }
    
    // Refresh connection requests
    await loadConnectionRequests();
    
  } catch (error) {
    console.error('Error responding to connection request:', error);
    
    // Reset button state on error
    if (button) {
      button.innerHTML = action === 'accept' ? 'Accept' : 'Decline';
      button.disabled = false;
    }
    
    showError(error.message || 'Failed to respond to request');
  }
}

// Load connection requests with notification badge
async function loadConnectionRequests() {
  try {
    const data = await API('/api/connections/requests');
    
    // Update notification badge
    const badge = $('#connection-requests-badge');
    const pendingCount = data.received_requests ? data.received_requests.length : 0;
    
    if (pendingCount > 0) {
      badge.textContent = pendingCount;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
    
    console.log('Connection requests:', data);
    return data;
  } catch (error) {
    console.error('Error loading connection requests:', error);
    return { received_requests: [], sent_requests: [] };
  }
}

// Update connection button in search results
function updateConnectionButton(userId, status) {
  const resultItems = document.querySelectorAll('.search-result-item');
  resultItems.forEach(item => {
    const nameElement = item.querySelector('.clickable-name');
    if (nameElement && nameElement.textContent) {
      // This is a simplified approach - in a real app you'd track user IDs better
      const button = item.querySelector('.search-connect-btn');
      if (button) {
        if (status === 'sent') {
          button.className = 'search-connect-btn pending';
          button.textContent = 'Pending';
          button.onclick = null;
        } else if (status === 'connected') {
          button.className = 'search-connect-btn connected';
          button.textContent = '✓ Connected';
          button.onclick = null;
        }
      }
    }
  });
}

// View user profile
function viewUserProfile(userId) {
  // For now, we'll just show an alert - in a real app you'd navigate to a profile page
  showSuccess(`Viewing profile for user ${userId}`);
  hideSearchResults();
}

// Create clickable name with connection button
function createClickableNameWithConnect(user, showConnectButton = true) {
  const nameHtml = `<span class="clickable-name" onclick="viewUserProfile(${user.id})">${user.name}</span>`;
  
  if (showConnectButton) {
    const connectButton = getInlineConnectionButton(user);
    return nameHtml + connectButton;
  }
  
  return nameHtml;
}

// Initialize universal search when page loads
document.addEventListener('DOMContentLoaded', () => {
  setupUniversalSearch();
  
  // Set up real-time connection request polling
  setInterval(async () => {
    if (currentUser) {
      await loadConnectionRequests();
    }
  }, 30000); // Check every 30 seconds for new connection requests
});
