import React, { useState, useEffect } from 'react';
import {
  api,
  AmenityItem,
  AmenitySlotItem,
  AmenityBookingItem,
  UserProfile
} from '../api/client';
import { Language, translations } from '../i18n/translations';

interface AmenityBookingPageProps {
  user: UserProfile;
  selectedFlatId: string;
  lang: Language;
}

export const AmenityBookingPage: React.FC<AmenityBookingPageProps> = ({
  user,
  selectedFlatId,
  lang,
}) => {
  const t = translations[lang];
  const [amenities, setAmenities] = useState<AmenityItem[]>([]);
  const [selectedAmenity, setSelectedAmenity] = useState<AmenityItem | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('2026-11-06');
  const [slots, setSlots] = useState<AmenitySlotItem[]>([]);
  const [myBookings, setMyBookings] = useState<AmenityBookingItem[]>([]);
  const [activeTab, setActiveTab] = useState<'BROWSE' | 'MY_BOOKINGS'>('BROWSE');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [bookingSlot, setBookingSlot] = useState<AmenitySlotItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reference demo date 2026-11-06 + next 6 days
  const dateOptions = Array.from({ length: 7 }, (_, i) => {
    const d = new Date('2026-11-06T00:00:00Z');
    d.setDate(d.getDate() + i);
    return d.toISOString().split('T')[0];
  });

  useEffect(() => {
    loadAmenities();
    if (selectedFlatId) {
      loadMyBookings();
    }
  }, [selectedFlatId]);

  useEffect(() => {
    if (selectedAmenity && selectedDate) {
      loadSlots(selectedAmenity.id, selectedDate);
    }
  }, [selectedAmenity, selectedDate]);

  const loadAmenities = async () => {
    setLoading(true);
    try {
      const data = await api.listAmenities();
      setAmenities(data);
      if (data.length > 0 && !selectedAmenity) {
        setSelectedAmenity(data[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.error?.message || err.message || 'Failed to load amenities');
    } finally {
      setLoading(false);
    }
  };

  const loadSlots = async (amenityId: string, date: string) => {
    try {
      const data = await api.listAmenitySlots(amenityId, date);
      setSlots(data);
    } catch (err: any) {
      setErrorMsg(err.error?.message || err.message || 'Failed to load slots');
    }
  };

  const loadMyBookings = async () => {
    try {
      const data = await api.listAmenityBookings(selectedFlatId);
      setMyBookings(data);
    } catch (err: any) {
      console.error('Failed to load user bookings', err);
    }
  };

  const handleBookSlot = async () => {
    if (!bookingSlot || !selectedAmenity || !selectedFlatId) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const idempotencyKey = crypto.randomUUID ? crypto.randomUUID() : `book-${Date.now()}-${Math.random()}`;

    try {
      await api.bookAmenitySlot(selectedFlatId, bookingSlot.id, idempotencyKey);
      setSuccessMsg(`Booking confirmed for ${selectedAmenity.name}!`);
      setBookingSlot(null);
      await loadSlots(selectedAmenity.id, selectedDate);
      await loadMyBookings();
    } catch (err: any) {
      const msg = err.error?.message || err.detail || err.message || 'Booking failed';
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelBooking = async (bookingId: string) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) return;
    setErrorMsg(null);
    try {
      await api.cancelAmenityBooking(bookingId);
      setSuccessMsg('Booking cancelled successfully.');
      if (selectedAmenity && selectedDate) {
        await loadSlots(selectedAmenity.id, selectedDate);
      }
      await loadMyBookings();
    } catch (err: any) {
      setErrorMsg(err.error?.message || err.detail || err.message || 'Cancellation failed');
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '1rem auto', padding: '0 1rem' }}>
      {/* Top Header & Tab Navigation */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1rem'
      }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
            🏊 {t.amenities}
          </h2>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Book club facilities, sports courts & banquet spaces with immediate slot reservation
          </div>
        </div>

        <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '3px' }}>
          <button
            onClick={() => setActiveTab('BROWSE')}
            style={{
              minHeight: '48px',
              padding: '0.4rem 1rem',
              borderRadius: '6px',
              border: 'none',
              fontWeight: activeTab === 'BROWSE' ? 700 : 500,
              background: activeTab === 'BROWSE' ? '#ffffff' : 'transparent',
              color: activeTab === 'BROWSE' ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              boxShadow: activeTab === 'BROWSE' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
            }}
          >
            {t.book_slot}
          </button>
          <button
            onClick={() => setActiveTab('MY_BOOKINGS')}
            style={{
              minHeight: '48px',
              padding: '0.4rem 1rem',
              borderRadius: '6px',
              border: 'none',
              fontWeight: activeTab === 'MY_BOOKINGS' ? 700 : 500,
              background: activeTab === 'MY_BOOKINGS' ? '#ffffff' : 'transparent',
              color: activeTab === 'MY_BOOKINGS' ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              boxShadow: activeTab === 'MY_BOOKINGS' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
            }}
          >
            {t.my_bookings} ({myBookings.filter(b => b.status === 'CONFIRMED').length})
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: '#fee2e2',
          border: '1px solid #f87171',
          color: '#991b1b',
          fontSize: '0.85rem',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>⚠️ {errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}

      {successMsg && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          background: '#dcfce7',
          border: '1px solid #86efac',
          color: '#166534',
          fontSize: '0.85rem',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>✓ {successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}

      {activeTab === 'BROWSE' ? (
        <>
          {/* Amenity Picker Tabs */}
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            overflowX: 'auto',
            paddingBottom: '0.5rem',
            marginBottom: '1rem'
          }}>
            {amenities.map((amenity) => {
              const isSelected = selectedAmenity?.id === amenity.id;
              return (
                <button
                  key={amenity.id}
                  onClick={() => setSelectedAmenity(amenity)}
                  style={{
                    minHeight: '48px',
                    padding: '0.6rem 1rem',
                    borderRadius: '8px',
                    border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border)',
                    background: isSelected ? '#eff6ff' : '#ffffff',
                    color: isSelected ? 'var(--primary)' : 'var(--text-main)',
                    fontWeight: isSelected ? 700 : 500,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    textAlign: 'left'
                  }}
                >
                  <div style={{ fontSize: '0.9rem' }}>{amenity.name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Fee: ₹{amenity.hourly_fee} / slot
                  </div>
                </button>
              );
            })}
          </div>

          {selectedAmenity && (
            <div style={{
              background: '#ffffff',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              padding: '1.25rem',
              marginBottom: '1.25rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
                    {selectedAmenity.name}
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {selectedAmenity.description || 'Clubhouse facility'} • Max Capacity: {selectedAmenity.capacity}
                  </div>
                </div>

                {/* Date Picker */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    Date:
                  </label>
                  <select
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    style={{
                      minHeight: '48px',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      border: '1px solid var(--border)',
                      fontWeight: 600,
                      fontSize: '0.85rem'
                    }}
                  >
                    {dateOptions.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Slot Cards Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: '0.75rem',
                marginTop: '1rem'
              }}>
                {slots.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
                    No time slots configured for this date.
                  </div>
                ) : (
                  slots.map((slot) => {
                    const isClosed = slot.is_closed;
                    const isFull = slot.booked_count >= slot.capacity;
                    const availableCount = slot.available_spots ?? Math.max(0, slot.capacity - slot.booked_count);
                    const canBook = !isClosed && !isFull;

                    return (
                      <div
                        key={slot.id}
                        style={{
                          border: isClosed
                            ? '1px solid #fecaca'
                            : isFull
                            ? '1px solid #e2e8f0'
                            : '1px solid #bfdbfe',
                          background: isClosed
                            ? '#fef2f2'
                            : isFull
                            ? '#f8fafc'
                            : '#ffffff',
                          borderRadius: '8px',
                          padding: '0.85rem',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '0.6rem'
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '0.9rem', color: isClosed ? '#991b1b' : 'var(--text-main)' }}>
                            ⏰ {slot.start_time.slice(0, 5)} - {slot.end_time.slice(0, 5)}
                          </div>
                          {isClosed ? (
                            <div style={{ fontSize: '0.75rem', color: '#b91c1c', marginTop: '0.25rem' }}>
                              🚫 Closed: {slot.closure_reason || 'Maintenance'}
                            </div>
                          ) : (
                            <div style={{ fontSize: '0.75rem', color: isFull ? '#64748b' : '#047857', marginTop: '0.25rem' }}>
                              {isFull ? '🔴 Capacity Full' : `🟢 ${availableCount} of ${slot.capacity} available`}
                            </div>
                          )}
                        </div>

                        <button
                          disabled={!canBook}
                          onClick={() => setBookingSlot(slot)}
                          style={{
                            minHeight: '48px',
                            width: '100%',
                            border: 'none',
                            borderRadius: '6px',
                            background: canBook ? 'var(--primary)' : '#cbd5e1',
                            color: '#ffffff',
                            fontWeight: 700,
                            fontSize: '0.85rem',
                            cursor: canBook ? 'pointer' : 'not-allowed',
                            transition: 'background 0.15s ease'
                          }}
                        >
                          {isClosed ? 'Closed' : isFull ? 'Full' : `${t.book_slot} (₹${selectedAmenity.hourly_fee})`}
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        /* My Bookings Tab */
        <div style={{
          background: '#ffffff',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem'
        }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>
            {t.my_bookings}
          </h3>

          {myBookings.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
              No amenity bookings found for this flat.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {myBookings.map((b) => {
                const isConfirmed = b.status === 'CONFIRMED';
                return (
                  <div
                    key={b.id}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      padding: '1rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '0.75rem'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        {b.amenity_name || 'Amenity'} • {b.slot_date}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        Slot: {b.start_time ? b.start_time.slice(0, 5) : ''} - {b.end_time ? b.end_time.slice(0, 5) : ''} • Fee: ₹{b.fee}
                      </div>
                      <div style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
                        Status: <strong style={{
                          color: isConfirmed ? '#16a34a' : b.status === 'CANCELLED' ? '#dc2626' : '#2563eb'
                        }}>{b.status}</strong>
                      </div>
                    </div>

                    {isConfirmed && (
                      <button
                        onClick={() => handleCancelBooking(b.id)}
                        style={{
                          minHeight: '48px',
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          border: '1px solid #fca5a5',
                          background: '#fff1f2',
                          color: '#b91c1c',
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          cursor: 'pointer'
                        }}
                      >
                        {t.cancel_booking}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Booking Confirmation Modal */}
      {bookingSlot && selectedAmenity && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            maxWidth: '440px',
            width: '100%',
            padding: '1.5rem',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 800, margin: '0 0 0.5rem 0' }}>
              Confirm Amenity Booking
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
              This will reserve the slot for your flat.
            </p>

            <div style={{
              background: '#f8fafc',
              borderRadius: '8px',
              padding: '0.85rem',
              fontSize: '0.85rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem',
              marginBottom: '1.25rem'
            }}>
              <div><strong>Amenity:</strong> {selectedAmenity.name}</div>
              <div><strong>Date:</strong> {selectedDate}</div>
              <div><strong>Time Slot:</strong> {bookingSlot.start_time.slice(0, 5)} - {bookingSlot.end_time.slice(0, 5)}</div>
              <div><strong>Fee Amount:</strong> ₹{selectedAmenity.hourly_fee}</div>
              <div><strong>Daily Rule:</strong> Max 1 booking per flat per day</div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                disabled={isSubmitting}
                onClick={() => setBookingSlot(null)}
                style={{
                  minHeight: '48px',
                  padding: '0.6rem 1.2rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  background: '#ffffff',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t.close}
              </button>
              <button
                disabled={isSubmitting}
                onClick={handleBookSlot}
                style={{
                  minHeight: '48px',
                  padding: '0.6rem 1.2rem',
                  borderRadius: '6px',
                  border: 'none',
                  background: 'var(--primary)',
                  color: '#ffffff',
                  fontWeight: 700,
                  cursor: isSubmitting ? 'not-allowed' : 'pointer'
                }}
              >
                {isSubmitting ? t.processing : 'Confirm Reservation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
