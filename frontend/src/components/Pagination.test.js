import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Pagination from './Pagination.vue'

function pageLabels(wrapper) {
  return wrapper.findAll('.page-btn:not(.nav-btn)').map((b) => b.text())
}

describe('Pagination', () => {
  it('renders nothing when there is only one page', () => {
    const wrapper = mount(Pagination, { props: { total: 3, page: 1, pageSize: 5 } })
    expect(wrapper.find('.pagination').exists()).toBe(false)
  })

  it('shows every page number when there are few pages', () => {
    const wrapper = mount(Pagination, { props: { total: 15, page: 1, pageSize: 5 } })
    expect(pageLabels(wrapper)).toEqual(['1', '2', '3'])
  })

  it('windows around the current page with ellipsis on a long list', () => {
    // 20 pages, sitting on page 10 — should show 1, …, 9, 10, 11, …, 20
    const wrapper = mount(Pagination, { props: { total: 100, page: 10, pageSize: 5 } })
    expect(pageLabels(wrapper)).toEqual(['1', '…', '9', '10', '11', '…', '20'])
  })

  it('does not double up the ellipsis when the window touches an edge', () => {
    // Page 2 of 20 — window is 1,2,3 plus the pinned last page 20; the gap
    // between 3 and 20 is a single ellipsis, not two.
    const wrapper = mount(Pagination, { props: { total: 100, page: 2, pageSize: 5 } })
    expect(pageLabels(wrapper)).toEqual(['1', '2', '3', '…', '20'])
  })

  it('marks the current page active and disables prev/next at the edges', () => {
    const wrapper = mount(Pagination, { props: { total: 15, page: 1, pageSize: 5 } })
    const active = wrapper.find('.page-btn.active')
    expect(active.text()).toBe('1')
    expect(wrapper.find('.nav-btn[aria-label="Previous page"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.nav-btn[aria-label="Next page"]').attributes('disabled')).toBeUndefined()
  })

  it('emits update:page with the clicked page number', async () => {
    const wrapper = mount(Pagination, { props: { total: 15, page: 1, pageSize: 5 } })
    const buttons = wrapper.findAll('.page-btn:not(.nav-btn)')
    await buttons[1].trigger('click') // page "2"
    expect(wrapper.emitted('update:page')).toEqual([[2]])
  })

  it('emits update:page when Next is clicked, and never for a disabled edge', async () => {
    const wrapper = mount(Pagination, { props: { total: 15, page: 1, pageSize: 5 } })
    await wrapper.find('.nav-btn[aria-label="Next page"]').trigger('click')
    expect(wrapper.emitted('update:page')).toEqual([[2]])

    const atStart = mount(Pagination, { props: { total: 15, page: 1, pageSize: 5 } })
    await atStart.find('.nav-btn[aria-label="Previous page"]').trigger('click')
    expect(atStart.emitted('update:page')).toBeUndefined()
  })

  it('never emits for the ellipsis placeholder', async () => {
    const wrapper = mount(Pagination, { props: { total: 100, page: 10, pageSize: 5 } })
    const dots = wrapper.findAll('.page-btn.dots')
    expect(dots.length).toBeGreaterThan(0)
    await dots[0].trigger('click')
    expect(wrapper.emitted('update:page')).toBeUndefined()
  })
})
